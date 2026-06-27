import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as s3n from "aws-cdk-lib/aws-s3-notifications";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as aoss from "aws-cdk-lib/aws-opensearchserverless";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";
import * as path from "path";

export class IngestionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const prefix          = "ingestion-pipeline";
    const collectionName  = `${prefix}-vectors`;
    const indexName       = process.env.OPENSEARCH_INDEX     ?? "document-chunks";
    const vpcId           = process.env.VPC_ID               ?? "";
    const subnetIds       = (process.env.SUBNET_IDS          ?? "").split(",").filter(Boolean);
    const securityGroupIds = (process.env.SECURITY_GROUP_IDS ?? "").split(",").filter(Boolean);
    const routeTableIds   = (process.env.ROUTE_TABLE_IDS     ?? "").split(",").filter(Boolean);
    const bedrockModelId  = process.env.BEDROCK_MODEL_ID     ?? "amazon.titan-embed-text-v2:0";
    const bedrockFallback = process.env.BEDROCK_FALLBACK_MODEL_ID ?? "cohere.embed-english-v3";

    // ── S3 raw bucket ──────────────────────────────────────────────────────────
    const rawBucket = new s3.Bucket(this, "RawBucket", {
      bucketName: `${prefix}-raw`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // ── SQS upload queue ───────────────────────────────────────────────────────
    const uploadDlq = new sqs.Queue(this, "UploadDlq", {
      queueName: `${prefix}-upload-dlq`,
      retentionPeriod: cdk.Duration.days(14),
    });

    const uploadQueue = new sqs.Queue(this, "UploadQueue", {
      queueName: `${prefix}-upload`,
      visibilityTimeout: cdk.Duration.seconds(300),
      deadLetterQueue: { queue: uploadDlq, maxReceiveCount: 3 },
    });

    rawBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.SqsDestination(uploadQueue),
      { prefix: "upload/raw/" }
    );

    // ── DynamoDB document tracking table ──────────────────────────────────────
    const documentsTable = new dynamodb.Table(this, "DocumentsTable", {
      tableName: `${prefix}-documents`,
      partitionKey: { name: "document_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: "expires_at",
    });

    // ── VPC endpoints for private subnet access ────────────────────────────────

    // S3 Gateway endpoint — free
    new ec2.CfnVPCEndpoint(this, "S3Endpoint", {
      vpcId,
      serviceName: `com.amazonaws.${this.region}.s3`,
      vpcEndpointType: "Gateway",
      routeTableIds,
    });

    // DynamoDB Gateway endpoint — free
    new ec2.CfnVPCEndpoint(this, "DynamoDbEndpoint", {
      vpcId,
      serviceName: `com.amazonaws.${this.region}.dynamodb`,
      vpcEndpointType: "Gateway",
      routeTableIds,
    });

    const interfaceEndpointDefaults = {
      vpcId,
      vpcEndpointType: "Interface",
      subnetIds,
      securityGroupIds,
      privateDnsEnabled: true,
    };

    new ec2.CfnVPCEndpoint(this, "EcrApiEndpoint",      { ...interfaceEndpointDefaults, serviceName: `com.amazonaws.${this.region}.ecr.api` });
    new ec2.CfnVPCEndpoint(this, "EcrDkrEndpoint",      { ...interfaceEndpointDefaults, serviceName: `com.amazonaws.${this.region}.ecr.dkr` });
    new ec2.CfnVPCEndpoint(this, "BedrockEndpoint",     { ...interfaceEndpointDefaults, serviceName: `com.amazonaws.${this.region}.bedrock-runtime` });
    new ec2.CfnVPCEndpoint(this, "LogsEndpoint",        { ...interfaceEndpointDefaults, serviceName: `com.amazonaws.${this.region}.logs` });
    new ec2.CfnVPCEndpoint(this, "StsEndpoint",         { ...interfaceEndpointDefaults, serviceName: `com.amazonaws.${this.region}.sts` });
    new ec2.CfnVPCEndpoint(this, "XRayEndpoint",        { ...interfaceEndpointDefaults, serviceName: `com.amazonaws.${this.region}.xray` });

    // ── OpenSearch Serverless ──────────────────────────────────────────────────
    const aossVpce = new aoss.CfnVpcEndpoint(this, "AossVpce", {
      name: `${prefix}-vpce`,
      vpcId,
      subnetIds,
      securityGroupIds,
    });

    const encPolicy = new aoss.CfnSecurityPolicy(this, "AossEncPolicy", {
      name: `${prefix}-enc`,
      type: "encryption",
      policy: JSON.stringify({
        Rules: [{ ResourceType: "collection", Resource: [`collection/${collectionName}`] }],
        AWSOwnedKey: true,
      }),
    });

    const netPolicy = new aoss.CfnSecurityPolicy(this, "AossNetPolicy", {
      name: `${prefix}-net`,
      type: "network",
      policy: JSON.stringify([
        {
          Rules: [{ ResourceType: "collection", Resource: [`collection/${collectionName}`] }],
          AllowFromPublic: false,
          SourceVPCEs: [aossVpce.attrId],
        },
        {
          Rules: [{ ResourceType: "dashboard", Resource: [`collection/${collectionName}`] }],
          AllowFromPublic: true,
        },
      ]),
    });
    netPolicy.addDependency(aossVpce);

    const collection = new aoss.CfnCollection(this, "VectorCollection", {
      name: collectionName,
      type: "VECTORSEARCH",
    });
    collection.addDependency(encPolicy);
    collection.addDependency(netPolicy);

    // ── ECR + ECS ──────────────────────────────────────────────────────────────
    const ecrRepo = new ecr.Repository(this, "DoclingWorkerRepo", {
      repositoryName: `${prefix}/docling-worker`,
      imageScanOnPush: true,
    });

    const cluster = new ecs.Cluster(this, "Cluster", {
      clusterName: `${prefix}-cluster`,
    });

    const taskRole = new iam.Role(this, "EcsTaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ["s3:GetObject"],
      resources: [`${rawBucket.bucketArn}/upload/raw/*`],
    }));

    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [
        `arn:aws:bedrock:${this.region}::foundation-model/${bedrockModelId}`,
        `arn:aws:bedrock:${this.region}::foundation-model/${bedrockFallback}`,
      ],
    }));

    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ["aoss:APIAccessAll"],
      resources: [collection.attrArn],
    }));

    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ["dynamodb:UpdateItem"],
      resources: [documentsTable.tableArn],
    }));

    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"],
      resources: ["*"],
    }));

    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      resources: ["*"],
    }));

    const dataAccessPolicy = new aoss.CfnAccessPolicy(this, "AossDataAccessPolicy", {
      name: `${prefix}-access`,
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {
            ResourceType: "index",
            Resource: [`index/${collectionName}/*`],
            Permission: ["aoss:CreateIndex", "aoss:DescribeIndex", "aoss:UpdateIndex", "aoss:WriteDocument", "aoss:ReadDocument"],
          },
          {
            ResourceType: "collection",
            Resource: [`collection/${collectionName}`],
            Permission: ["aoss:CreateCollectionItems"],
          },
        ],
        Principal: [taskRole.roleArn],
      }]),
    });
    dataAccessPolicy.addDependency(collection);

    const logGroup = new logs.LogGroup(this, "DoclingWorkerLogs", {
      logGroupName: `/ecs/${prefix}/docling-worker`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const xrayLogGroup = new logs.LogGroup(this, "XRayDaemonLogs", {
      logGroupName: `/ecs/${prefix}/xray-daemon`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const taskDef = new ecs.FargateTaskDefinition(this, "DoclingWorkerTask", {
      family: `${prefix}-docling-worker`,
      cpu: 2048,
      memoryLimitMiB: 8192,
      taskRole,
    });

    taskDef.addContainer("docling-worker", {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepo, "latest"),
      environment: {
        BEDROCK_MODEL_ID:          bedrockModelId,
        BEDROCK_FALLBACK_MODEL_ID: bedrockFallback,
        EMBEDDING_DIMENSIONS:      process.env.EMBEDDING_DIMENSIONS ?? "1024",
        MAX_TOKENS:                process.env.MAX_TOKENS           ?? "512",
        MAX_WORKERS:               process.env.MAX_WORKERS          ?? "1",
        AWS_REGION:                this.region,
        OPENSEARCH_ENDPOINT:       collection.attrCollectionEndpoint,
        OPENSEARCH_INDEX:          indexName,
        DYNAMODB_TABLE:            documentsTable.tableName,
        AWS_XRAY_DAEMON_ADDRESS:   "127.0.0.1:2000",
      },
      logging: ecs.LogDrivers.awsLogs({ logGroup, streamPrefix: "ecs" }),
    });

    taskDef.addContainer("xray-daemon", {
      image: ecs.ContainerImage.fromRegistry("public.ecr.aws/xray/aws-xray-daemon:latest"),
      cpu: 32,
      memoryReservationMiB: 256,
      essential: false,
      portMappings: [{ containerPort: 2000, protocol: ecs.Protocol.UDP }],
      logging: ecs.LogDrivers.awsLogs({ logGroup: xrayLogGroup, streamPrefix: "ecs" }),
    });

    // ── Kickstarter Lambda ─────────────────────────────────────────────────────
    const kickstarterRole = new iam.Role(this, "KickstarterRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    kickstarterRole.addToPolicy(new iam.PolicyStatement({
      actions: ["ecs:RunTask"],
      resources: [taskDef.taskDefinitionArn],
    }));

    kickstarterRole.addToPolicy(new iam.PolicyStatement({
      actions: ["iam:PassRole"],
      resources: [taskRole.roleArn],
    }));

    kickstarterRole.addToPolicy(new iam.PolicyStatement({
      actions: ["dynamodb:PutItem"],
      resources: [documentsTable.tableArn],
    }));

    kickstarterRole.addToPolicy(new iam.PolicyStatement({
      actions: ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"],
      resources: ["*"],
    }));

    kickstarterRole.addToPolicy(new iam.PolicyStatement({
      actions: ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      resources: ["*"],
    }));

    const kickstarter = new lambda.Function(this, "Kickstarter", {
      functionName: `${prefix}-kickstarter`,
      runtime: lambda.Runtime.NODEJS_20_X,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../../workers/kickstarter"),
        { exclude: ["*.test.js", "node_modules"] }
      ),
      role: kickstarterRole,
      timeout: cdk.Duration.seconds(30),
      tracing: lambda.Tracing.ACTIVE,
      environment: {
        ECS_CLUSTER:         cluster.clusterName,
        ECS_TASK_DEFINITION: taskDef.taskDefinitionArn,
        ECS_CONTAINER_NAME:  "docling-worker",
        SUBNETS:             subnetIds.join(","),
        SECURITY_GROUPS:     securityGroupIds.join(","),
        DYNAMODB_TABLE:      documentsTable.tableName,
      },
    });

    kickstarter.addEventSource(
      new lambdaEventSources.SqsEventSource(uploadQueue, { batchSize: 1 })
    );

    // ── Outputs ────────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, "RawBucketName",      { value: rawBucket.bucketName });
    new cdk.CfnOutput(this, "UploadQueueUrl",     { value: uploadQueue.queueUrl });
    new cdk.CfnOutput(this, "EcrRepoUrl",         { value: ecrRepo.repositoryUri });
    new cdk.CfnOutput(this, "EcsClusterArn",      { value: cluster.clusterArn });
    new cdk.CfnOutput(this, "OpenSearchEndpoint", { value: collection.attrCollectionEndpoint });
    new cdk.CfnOutput(this, "DocumentsTableName",  { value: documentsTable.tableName });
  }
}
