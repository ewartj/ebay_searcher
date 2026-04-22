#!/usr/bin/env bash
# Deploy Warhammer Scout to AWS Lambda as a container image.
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - Docker running
#   - Terraform applied at least once (deploy/terraform/):
#       cd deploy/terraform && terraform init && terraform apply
#
# Usage:
#   ./deploy/deploy.sh                  # build, push, update Lambda
#   REGION=us-east-1 ./deploy/deploy.sh # override region

set -euo pipefail

REGION="${REGION:-eu-west-2}"
REPO_NAME="warhammer-scout"
FUNCTION_NAME="warhammer-scout"

# Prefer Terraform output; fall back to constructing the URI from the account ID.
TF_DIR="$(dirname "$0")/terraform"
if command -v terraform &>/dev/null && [ -f "${TF_DIR}/.terraform/terraform.tfstate" -o -f "${TF_DIR}/terraform.tfstate" ]; then
  ECR_URI=$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url 2>/dev/null || true)
fi
if [ -z "${ECR_URI:-}" ]; then
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"
fi

# ECR registry hostname is the part of the URI before the first '/'
ECR_REGISTRY="${ECR_URI%%/*}"

echo "==> Logging in to ECR..."
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "==> Building image..."
docker build \
  --platform linux/amd64 \
  -f deploy/Dockerfile.lambda \
  -t "${REPO_NAME}:latest" \
  .

echo "==> Tagging and pushing..."
docker tag "${REPO_NAME}:latest" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"

echo "==> Updating Lambda functions..."
for fn in "warhammer-scout" "warhammer-scout-weekly" "warhammer-scout-alerts"; do
  aws lambda update-function-code \
    --function-name "$fn" \
    --image-uri "${ECR_URI}:latest" \
    --region "$REGION" \
    --output text --query 'FunctionArn'
done

echo "==> Done. All Lambda functions updated."
