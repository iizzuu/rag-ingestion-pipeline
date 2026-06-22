variable "aws_region" {
  description = "AWS region"
  default     = "eu-west-2"
}

variable "project" {
  description = "Resource name prefix"
  default     = "ingestion-pipeline"
}

variable "vpc_id" {
  description = "VPC ID for ECS tasks"
}

variable "subnet_ids" {
  description = "Subnet IDs for ECS tasks (comma-separated list)"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for ECS tasks"
  type        = list(string)
}

variable "vector_store" {
  description = "Vector store to use: supabase | pinecone | qdrant"
  default     = "supabase"
  validation {
    condition     = contains(["supabase", "pinecone", "qdrant"], var.vector_store)
    error_message = "vector_store must be supabase, pinecone, or qdrant."
  }
}

variable "supabase_url" { default = "" }
variable "supabase_service_key" {
  default   = ""
  sensitive = true
}
variable "pinecone_api_key" {
  default   = ""
  sensitive = true
}
variable "pinecone_index_name" { default = "" }
variable "qdrant_url"          { default = "" }
variable "qdrant_api_key" {
  default   = ""
  sensitive = true
}
variable "qdrant_collection" { default = "" }

variable "bedrock_model_id"     { default = "amazon.titan-embed-text-v2:0" }
variable "embedding_dimensions" { default = "1024" }
variable "max_tokens"           { default = "512" }
variable "max_workers"          { default = "10" }

variable "docling_worker_image" {
  description = "ECR image URI for the Docling ECS task (set after docker push)"
  default     = ""
}
