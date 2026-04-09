#!/bin/bash
# Docker 이미지 빌드 및 ECR 푸시 스크립트

set -e

# 변수 설정
AWS_REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || true)}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
ECR_REPOSITORY_NAME="jupyter-manager"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# 색상 출력
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Jupyter Manager 이미지 빌드 및 푸시 ===${NC}"

# AWS 계정 ID 가져오기
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}AWS 계정 ID를 가져올 수 없습니다. AWS CLI가 올바르게 구성되었는지 확인하세요.${NC}"
    exit 1
fi

echo -e "${YELLOW}AWS 계정 ID: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${YELLOW}리전: ${AWS_REGION}${NC}"

# ECR 리포지토리 URL
ECR_REPOSITORY_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"

# ECR 리포지토리 생성 (존재하지 않는 경우)
echo -e "\n${GREEN}1. ECR 리포지토리 확인/생성${NC}"
if ! aws ecr describe-repositories --repository-names ${ECR_REPOSITORY_NAME} --region ${AWS_REGION} > /dev/null 2>&1; then
    echo "리포지토리가 존재하지 않습니다. 생성 중..."
    aws ecr create-repository \
        --repository-name ${ECR_REPOSITORY_NAME} \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256
    echo -e "${GREEN}리포지토리 생성 완료${NC}"
else
    echo -e "${GREEN}리포지토리가 이미 존재합니다${NC}"
fi

# ECR 로그인
echo -e "\n${GREEN}2. ECR 로그인${NC}"
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Docker 이미지 빌드
echo -e "\n${GREEN}3. Docker 이미지 빌드${NC}"
cd app
docker build -t ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} .
docker tag ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY_URL}:${IMAGE_TAG}
docker tag ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY_URL}:v1.0.0
cd ..

# ECR에 푸시
echo -e "\n${GREEN}4. ECR에 이미지 푸시${NC}"
docker push ${ECR_REPOSITORY_URL}:${IMAGE_TAG}
docker push ${ECR_REPOSITORY_URL}:v1.0.0

echo -e "\n${GREEN}=== 완료! ===${NC}"
echo -e "${YELLOW}이미지 URL: ${ECR_REPOSITORY_URL}:${IMAGE_TAG}${NC}"
echo -e "\n${YELLOW}다음 단계:${NC}"
echo "1. kube-manifests/02-backend-deployment.yml 파일 편집"
echo "2. <YOUR_ECR_REPOSITORY_URL>을 다음으로 변경:"
echo -e "   ${GREEN}${ECR_REPOSITORY_URL}${NC}"
echo "3. kubectl apply -f kube-manifests/ 실행"
