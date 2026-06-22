resource "aws_ecr_repository" "docling_worker" {
  name                 = "${local.prefix}/docling-worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
