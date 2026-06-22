resource "aws_ecs_cluster" "main" {
  name = "${local.prefix}-cluster"
}

resource "aws_cloudwatch_log_group" "docling_worker" {
  name              = "/ecs/${local.prefix}/docling-worker"
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

  container_definitions = jsonencode([{
    name  = "docling-worker"
    image = var.docling_worker_image != "" ? var.docling_worker_image : "${aws_ecr_repository.docling_worker.repository_url}:latest"
    environment = [
      { name = "VECTOR_STORE",         value = var.vector_store },
      { name = "SUPABASE_URL",         value = var.supabase_url },
      { name = "SUPABASE_SERVICE_KEY", value = var.supabase_service_key },
      { name = "PINECONE_API_KEY",     value = var.pinecone_api_key },
      { name = "PINECONE_INDEX_NAME",  value = var.pinecone_index_name },
      { name = "QDRANT_URL",           value = var.qdrant_url },
      { name = "QDRANT_API_KEY",       value = var.qdrant_api_key },
      { name = "QDRANT_COLLECTION",    value = var.qdrant_collection },
      { name = "BEDROCK_MODEL_ID",     value = var.bedrock_model_id },
      { name = "EMBEDDING_DIMENSIONS", value = var.embedding_dimensions },
      { name = "MAX_TOKENS",           value = var.max_tokens },
      { name = "MAX_WORKERS",          value = var.max_workers },
      { name = "AWS_REGION",           value = var.aws_region },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.docling_worker.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}
