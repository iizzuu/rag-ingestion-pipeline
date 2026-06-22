resource "aws_sqs_queue" "upload_dlq" {
  name                      = "${local.prefix}-upload-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "upload" {
  name                       = "${local.prefix}-upload"
  visibility_timeout_seconds = 300
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.upload_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue_policy" "upload" {
  queue_url = aws_sqs_queue.upload.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.upload.arn
      Condition = {
        ArnLike = { "aws:SourceArn" = aws_s3_bucket.raw.arn }
      }
    }]
  })
}
