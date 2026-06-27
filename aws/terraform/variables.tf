variable "aws_region" {
  description = "AWS region"
  default     = "eu-west-2"
}

variable "project" {
  description = "Resource name prefix"
  default     = "ingestion-pipeline"
}

variable "vpc_id" {
  description = "VPC ID for ECS tasks and OpenSearch VPC endpoint"
}

variable "subnet_ids" {
  description = "Subnet IDs for ECS tasks and OpenSearch VPC endpoint"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for ECS tasks and OpenSearch VPC endpoint"
  type        = list(string)
}

variable "route_table_ids" {
  description = "Route table IDs for the private subnets (needed for S3 Gateway endpoint)"
  type        = list(string)
}

variable "opensearch_index" {
  description = "OpenSearch index name for document chunks"
  default     = "document-chunks"
}

variable "bedrock_model_id"          { default = "amazon.titan-embed-text-v2:0" }
variable "bedrock_fallback_model_id" { default = "cohere.embed-english-v3" }
variable "embedding_dimensions" { default = "1024" }
variable "max_tokens"           { default = "512" }
variable "max_workers"          { default = "10" }

variable "docling_worker_image" {
  description = "ECR image URI for the Docling ECS task (set after docker push)"
  default     = ""
}
