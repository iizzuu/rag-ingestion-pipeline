const { ECSClient, RunTaskCommand } = require("@aws-sdk/client-ecs");

const ecs = new ECSClient({ region: process.env.AWS_REGION ?? "eu-west-2" });

exports.handler = async (event) => {
  for (const record of event.Records) {
    const body = JSON.parse(record.body);
    const s3Record = body.Records?.[0];
    if (!s3Record) continue;

    const bucket = s3Record.s3.bucket.name;
    const key = decodeURIComponent(s3Record.s3.object.key.replace(/\+/g, " "));
    const documentId = key.split("/")[2];

    console.log(`Triggering ECS: documentId=${documentId} key=${key}`);

    await ecs.send(
      new RunTaskCommand({
        cluster: process.env.ECS_CLUSTER,
        taskDefinition: process.env.ECS_TASK_DEFINITION,
        launchType: "FARGATE",
        networkConfiguration: {
          awsvpcConfiguration: {
            subnets: process.env.SUBNETS.split(","),
            securityGroups: process.env.SECURITY_GROUPS.split(","),
            assignPublicIp: "ENABLED",
          },
        },
        overrides: {
          containerOverrides: [
            {
              name: process.env.ECS_CONTAINER_NAME,
              environment: [
                { name: "BUCKET", value: bucket },
                { name: "KEY", value: key },
                { name: "DOCUMENT_ID", value: documentId },
              ],
            },
          ],
        },
      })
    );
  }
};
