# AWS Deployment

Event-driven ingestion. One ECS Fargate task per document. Scales to zero between jobs.

## Architecture

```
Client → POST /presign → Express API
Client → PUT → S3 (upload/raw/{documentId}/file)
S3 event → SQS → Lambda Kickstarter → ECS RunTask
ECS Fargate (Docling Worker):
  parse → chunk → embed (Bedrock Titan) → store
```

## Prerequisites

- AWS account with Bedrock access (Titan Embed v2 enabled in your region)
- AWS CLI configured (`aws configure`)
- Terraform ≥ 1.7 or Node.js 20 + AWS CDK v2
- Docker (to build and push the Docling worker image)
- A VPC with at least one public subnet

## Deploy with Terraform

```bash
cd aws/terraform
terraform init

terraform apply \
  -var="vpc_id=vpc-xxxxxxxx" \
  -var='subnet_ids=["subnet-aaa","subnet-bbb"]' \
  -var='security_group_ids=["sg-111"]' \
  -var="vector_store=supabase" \
  -var="supabase_url=https://your-project.supabase.co" \
  -var="supabase_service_key=your-service-role-key"
```

Then build and push the Docling worker image:

```bash
ECR_URL=$(terraform output -raw ecr_repo_url)
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
docker build -t $ECR_URL:latest aws/workers/docling-worker/
docker push $ECR_URL:latest
```

## Deploy with CDK

```bash
cd aws/cdk
npm install
npm run build

export VECTOR_STORE=supabase
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_KEY=your-service-role-key
export SUBNET_IDS=subnet-aaa,subnet-bbb
export SECURITY_GROUP_IDS=sg-111

npx cdk deploy
```

## Swap your vector store

Change `VECTOR_STORE` (and the corresponding credentials) in `variables.tf` or your environment before deploying. The Terraform and CDK stacks pass the value directly into the ECS task as an environment variable.

## Run the tests

```bash
# Python workers
cd aws/workers/docling-worker
python -m pytest tests/ -v

# Kickstarter Lambda
cd aws/workers/kickstarter
npm test
```

## Supported file types

PDF, DOCX, TXT, MD, CSV, JSON
