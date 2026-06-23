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
import { Construct } from "constructs";
import * as path from "path";

export class IngestionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const vectorStore = process.env.VECTOR_STORE ?? "supabase";
    const prefix = "ingestion-pipeline";

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

    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["s3:GetObject"],
        resources: [`${rawBucket.bucketArn}/upload/raw/*`],
      })
    );

    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          `arn:aws:bedrock:${this.region}::foundation-model/${process.env.BEDROCK_MODEL_ID ?? "amazon.titan-embed-text-v2:0"}`
        ],
      })
    );

    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        resources: ["*"],
      })
    );

    const logGroup = new logs.LogGroup(this, "DoclingWorkerLogs", {
      logGroupName: `/ecs/${prefix}/docling-worker`,
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
        VECTOR_STORE: vectorStore,
        SUPABASE_URL: process.env.SUPABASE_URL ?? "",
        SUPABASE_SERVICE_KEY: process.env.SUPABASE_SERVICE_KEY ?? "",
        PINECONE_API_KEY: process.env.PINECONE_API_KEY ?? "",
        PINECONE_INDEX_NAME: process.env.PINECONE_INDEX_NAME ?? "",
        QDRANT_URL: process.env.QDRANT_URL ?? "",
        QDRANT_API_KEY: process.env.QDRANT_API_KEY ?? "",
        QDRANT_COLLECTION: process.env.QDRANT_COLLECTION ?? "",
        BEDROCK_MODEL_ID: process.env.BEDROCK_MODEL_ID ?? "amazon.titan-embed-text-v2:0",
        EMBEDDING_DIMENSIONS: process.env.EMBEDDING_DIMENSIONS ?? "1024",
        MAX_TOKENS: process.env.MAX_TOKENS ?? "512",
        MAX_WORKERS: process.env.MAX_WORKERS ?? "10",
      },
      logging: ecs.LogDrivers.awsLogs({
        logGroup,
        streamPrefix: "ecs",
      }),
    });

    // ── Kickstarter Lambda ─────────────────────────────────────────────────────
    const kickstarterRole = new iam.Role(this, "KickstarterRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    kickstarterRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ecs:RunTask"],
        resources: [taskDef.taskDefinitionArn],
      })
    );

    kickstarterRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["iam:PassRole"],
        resources: [taskRole.roleArn],
      })
    );

    kickstarterRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        resources: ["*"],
      })
    );

    const subnetIds = (process.env.SUBNET_IDS ?? "").split(",").filter(Boolean);
    const securityGroupIds = (process.env.SECURITY_GROUP_IDS ?? "").split(",").filter(Boolean);

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
      environment: {
        ECS_CLUSTER: cluster.clusterName,
        ECS_TASK_DEFINITION: taskDef.taskDefinitionArn,
        ECS_CONTAINER_NAME: "docling-worker",
        SUBNETS: subnetIds.join(","),
        SECURITY_GROUPS: securityGroupIds.join(","),
      },
    });

    kickstarter.addEventSource(
      new lambdaEventSources.SqsEventSource(uploadQueue, { batchSize: 1 })
    );

    // ── Outputs ────────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, "RawBucketName", { value: rawBucket.bucketName });
    new cdk.CfnOutput(this, "UploadQueueUrl", { value: uploadQueue.queueUrl });
    new cdk.CfnOutput(this, "EcrRepoUrl", { value: ecrRepo.repositoryUri });
    new cdk.CfnOutput(this, "EcsClusterArn", { value: cluster.clusterArn });
  }
}
