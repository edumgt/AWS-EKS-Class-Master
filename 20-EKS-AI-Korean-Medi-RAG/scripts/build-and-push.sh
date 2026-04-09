#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-northeast-2}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_REPO_API="${ECR_REPO_API:-ai-korean-medi-rag-api}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CHAPTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "${CHAPTER_DIR}/source/requirements.txt" ]]; then
  echo "Source is missing. Run ./scripts/sync-source.sh first."
  exit 1
fi

aws ecr describe-repositories --repository-names "${ECR_REPO_API}" --region "${AWS_REGION}" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "${ECR_REPO_API}" --region "${AWS_REGION}" >/dev/null

aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

API_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_API}:${IMAGE_TAG}"

docker build -f "${CHAPTER_DIR}/dockerfiles/api.Dockerfile" -t "${API_IMAGE}" "${CHAPTER_DIR}"
docker push "${API_IMAGE}"

echo "API_IMAGE=${API_IMAGE}"
