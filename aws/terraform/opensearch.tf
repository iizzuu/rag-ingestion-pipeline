resource "aws_opensearchserverless_vpc_endpoint" "main" {
  name               = "${local.prefix}-vpce"
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  security_group_ids = var.security_group_ids
}

resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${local.prefix}-enc"
  type = "encryption"
  policy = jsonencode({
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${local.prefix}-vectors"]
    }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  name = "${local.prefix}-net"
  type = "network"
  policy = jsonencode([
    {
      Rules           = [{ ResourceType = "collection", Resource = ["collection/${local.prefix}-vectors"] }]
      AllowFromPublic = false
      SourceVPCEs     = [aws_opensearchserverless_vpc_endpoint.main.id]
    },
    {
      Rules           = [{ ResourceType = "dashboard", Resource = ["collection/${local.prefix}-vectors"] }]
      AllowFromPublic = true
    }
  ])
}

resource "aws_opensearchserverless_collection" "vectors" {
  name = "${local.prefix}-vectors"
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
  ]
}

resource "aws_opensearchserverless_access_policy" "data" {
  name = "${local.prefix}-access"
  type = "data"
  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "index"
        Resource     = ["index/${local.prefix}-vectors/*"]
        Permission = [
          "aoss:CreateIndex",
          "aoss:DescribeIndex",
          "aoss:UpdateIndex",
          "aoss:WriteDocument",
          "aoss:ReadDocument",
        ]
      },
      {
        ResourceType = "collection"
        Resource     = ["collection/${local.prefix}-vectors"]
        Permission   = ["aoss:CreateCollectionItems"]
      }
    ]
    Principal = [
      aws_iam_role.ecs_task.arn,
      "arn:aws:iam::166644096304:user/general-user",
    ]
  }])
}
