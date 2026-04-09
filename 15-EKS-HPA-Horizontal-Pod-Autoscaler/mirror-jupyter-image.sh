#!/bin/bash

set -euo pipefail

AWS_REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || true)}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
SOURCE_IMAGE="${SOURCE_IMAGE:-jupyter/minimal-notebook:latest}"
TARGET_REPOSITORY="${TARGET_REPOSITORY:-jupyter-minimal-notebook}"
TARGET_TAG="${TARGET_TAG:-latest}"

AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
TARGET_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${TARGET_REPOSITORY}:${TARGET_TAG}"

echo "=== Mirror Jupyter Image To ECR ==="
echo "Source: ${SOURCE_IMAGE}"
echo "Target: ${TARGET_IMAGE}"

if ! aws ecr describe-repositories --repository-names "${TARGET_REPOSITORY}" --region "${AWS_REGION}" >/dev/null 2>&1; then
  aws ecr create-repository \
    --repository-name "${TARGET_REPOSITORY}" \
    --region "${AWS_REGION}" \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 >/dev/null
fi

aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker pull "${SOURCE_IMAGE}"
docker tag "${SOURCE_IMAGE}" "${TARGET_IMAGE}"
docker push "${TARGET_IMAGE}"

echo "Mirrored image: ${TARGET_IMAGE}"
