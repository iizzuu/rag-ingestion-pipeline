resource "aws_s3_bucket" "raw" {
  bucket        = "${local.prefix}-raw"
  force_destroy = true
}

resource "aws_s3_bucket_notification" "raw" {
  bucket = aws_s3_bucket.raw.id

  queue {
    queue_arn     = aws_sqs_queue.upload.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "upload/raw/"
  }

  depends_on = [aws_sqs_queue_policy.upload]
}
