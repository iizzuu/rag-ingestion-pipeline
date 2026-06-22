data "archive_file" "kickstarter" {
  type        = "zip"
  source_dir  = "${path.module}/../workers/kickstarter"
  output_path = "${path.module}/kickstarter.zip"
  excludes    = ["node_modules", "*.test.js"]
}

resource "aws_lambda_function" "kickstarter" {
  function_name    = "${local.prefix}-kickstarter"
  role             = aws_iam_role.kickstarter.arn
  filename         = data.archive_file.kickstarter.output_path
  source_code_hash = data.archive_file.kickstarter.output_base64sha256
  handler          = "handler.handler"
  runtime          = "nodejs20.x"
  timeout          = 30

  environment {
    variables = {
      ECS_CLUSTER         = aws_ecs_cluster.main.name
      ECS_TASK_DEFINITION = aws_ecs_task_definition.docling_worker.arn
      ECS_CONTAINER_NAME  = "docling-worker"
      SUBNETS             = join(",", var.subnet_ids)
      SECURITY_GROUPS     = join(",", var.security_group_ids)
    }
  }
}

resource "aws_lambda_event_source_mapping" "kickstarter" {
  event_source_arn = aws_sqs_queue.upload.arn
  function_name    = aws_lambda_function.kickstarter.arn
  batch_size       = 1
}
