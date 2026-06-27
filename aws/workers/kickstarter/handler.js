const AWSXRay = require("aws-xray-sdk-core");
const { ECSClient, RunTaskCommand } = require("@aws-sdk/client-ecs");
const { DynamoDBClient, PutItemCommand } = require("@aws-sdk/client-dynamodb");

const ecsClient = AWSXRay.captureAWSv3Client(
  new ECSClient({ region: process.env.AWS_REGION ?? "eu-west-2" })
);
const dynamoClient = AWSXRay.captureAWSv3Client(
  new DynamoDBClient({ region: process.env.AWS_REGION ?? "eu-west-2" })
);

exports.handler = async (event) => {
  for (const record of event.Records) {
    const body = JSON.parse(record.body);
    const s3Record = body.Records?.[0];
    if (!s3Record) continue;

    const bucket     = s3Record.s3.bucket.name;
    const key        = decodeURIComponent(s3Record.s3.object.key.replace(/\+/g, " "));
    const documentId = key.split("/")[2];
    const filename   = key.split("/").pop();

    await dynamoClient.send(new PutItemCommand({
      TableName: process.env.DYNAMODB_TABLE,
      Item: {
        document_id: { S: documentId },
        filename:    { S: filename },
        s3_key:      { S: key },
        status:      { S: "processing" },
        created_at:  { S: new Date().toISOString() },
      },
    }));

    console.log(`Triggering ECS: documentId=${documentId} key=${key}`);

    await ecsClient.send(new RunTaskCommand({
      cluster:        process.env.ECS_CLUSTER,
      taskDefinition: process.env.ECS_TASK_DEFINITION,
      launchType:     "FARGATE",
      networkConfiguration: {
        awsvpcConfiguration: {
          subnets:        process.env.SUBNETS.split(","),
          securityGroups: process.env.SECURITY_GROUPS.split(","),
          assignPublicIp: "DISABLED",
        },
      },
      overrides: {
        containerOverrides: [{
          name: process.env.ECS_CONTAINER_NAME,
          environment: [
            { name: "BUCKET",      value: bucket },
            { name: "KEY",         value: key },
            { name: "DOCUMENT_ID", value: documentId },
            { name: "FILENAME",    value: filename },
          ],
        }],
      },
    }));
  }
};
