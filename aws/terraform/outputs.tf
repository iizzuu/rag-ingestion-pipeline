output "raw_bucket_name" {
  value = aws_s3_bucket.raw.bucket
}

output "upload_queue_url" {
  value = aws_sqs_queue.upload.url
}

output "ecr_repo_url" {
  value = aws_ecr_repository.docling_worker.repository_url
}

output "ecs_cluster_arn" {
  value = aws_ecs_cluster.main.arn
}
