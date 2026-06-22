const { mockClient } = require("@aws-sdk/client-ecs");

jest.mock("@aws-sdk/client-ecs", () => {
  const mockSend = jest.fn().mockResolvedValue({});
  return {
    ECSClient: jest.fn(() => ({ send: mockSend })),
    RunTaskCommand: jest.fn((input) => ({ input })),
    __mockSend: mockSend,
  };
});

const { handler } = require("./handler");

function makeEvent(bucket, key) {
  return {
    Records: [
      {
        body: JSON.stringify({
          Records: [
            {
              s3: {
                bucket: { name: bucket },
                object: { key: encodeURIComponent(key) },
              },
            },
          ],
        }),
      },
    ],
  };
}

beforeEach(() => {
  process.env.ECS_CLUSTER = "test-cluster";
  process.env.ECS_TASK_DEFINITION = "test-task-def";
  process.env.ECS_CONTAINER_NAME = "docling-worker";
  process.env.SUBNETS = "subnet-aaa,subnet-bbb";
  process.env.SECURITY_GROUPS = "sg-111";
});

test("calls RunTask with correct document_id extracted from key", async () => {
  const { RunTaskCommand } = require("@aws-sdk/client-ecs");
  const event = makeEvent("my-bucket", "upload/raw/doc-xyz/document.pdf");
  await handler(event);

  const callArg = RunTaskCommand.mock.calls[0][0];
  const overrides = callArg.overrides.containerOverrides[0].environment;
  const envMap = Object.fromEntries(overrides.map((e) => [e.name, e.value]));

  expect(envMap.BUCKET).toBe("my-bucket");
  expect(envMap.KEY).toBe("upload/raw/doc-xyz/document.pdf");
  expect(envMap.DOCUMENT_ID).toBe("doc-xyz");
});

test("skips record with no s3 event", async () => {
  const { RunTaskCommand } = require("@aws-sdk/client-ecs");
  RunTaskCommand.mockClear();
  const event = { Records: [{ body: JSON.stringify({}) }] };
  await handler(event);
  expect(RunTaskCommand).not.toHaveBeenCalled();
});
