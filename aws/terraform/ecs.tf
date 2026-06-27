resource "aws_ecs_cluster" "main" {
  name = "${local.prefix}-cluster"
}

resource "aws_cloudwatch_log_group" "docling_worker" {
  name              = "/ecs/${local.prefix}/docling-worker"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "xray_daemon" {
  name              = "/ecs/${local.prefix}/xray-daemon"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "docling_worker" {
  family                   = "${local.prefix}-docling-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "2048"
  memory                   = "8192"
  execution_role_arn       = aws_iam_role.ecs_task.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "docling-worker"
      image = var.docling_worker_image != "" ? var.docling_worker_image : "${aws_ecr_repository.docling_worker.repository_url}:latest"
      environment = [
        { name = "BEDROCK_MODEL_ID",          value = var.bedrock_model_id },
        { name = "BEDROCK_FALLBACK_MODEL_ID", value = var.bedrock_fallback_model_id },
        { name = "EMBEDDING_DIMENSIONS",      value = var.embedding_dimensions },
        { name = "MAX_TOKENS",                value = var.max_tokens },
        { name = "MAX_WORKERS",               value = var.max_workers },
        { name = "AWS_REGION",                value = var.aws_region },
        { name = "OPENSEARCH_ENDPOINT",       value = aws_opensearchserverless_collection.vectors.collection_endpoint },
        { name = "OPENSEARCH_INDEX",          value = var.opensearch_index },
        { name = "DYNAMODB_TABLE",            value = aws_dynamodb_table.documents.name },
        { name = "AWS_XRAY_DAEMON_ADDRESS",   value = "127.0.0.1:2000" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.docling_worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
    {
      name      = "xray-daemon"
      image     = "public.ecr.aws/xray/aws-xray-daemon:latest"
      cpu       = 32
      memory    = 256
      essential = false
      portMappings = [{
        containerPort = 2000
        protocol      = "udp"
      }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.xray_daemon.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}
