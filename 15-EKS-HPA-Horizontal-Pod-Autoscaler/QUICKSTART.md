# 빠른 시작 가이드

## 📋 사전 준비
1. EKS 클러스터 실행 중
2. kubectl 설정 완료
3. AWS CLI 설정 완료
4. Docker 설치

## 🚀 5분 안에 시작하기

### 1. 이미지 빌드 및 푸시
```bash
./mirror-jupyter-image.sh
./build-and-push.sh
```

### 2. ECR 이미지 URL 업데이트
기본값은 아래 ECR 경로로 설정되어 있습니다:
```bash
# 086015456585.dkr.ecr.ap-northeast-2.amazonaws.com/jupyter-manager:latest
# 086015456585.dkr.ecr.ap-northeast-2.amazonaws.com/jupyter-minimal-notebook:latest
```

다른 태그를 푸시했다면 `kube-manifests/02-backend-deployment.yml`의 image 값을 맞춰서 수정합니다.

### 3. 배포
```bash
# Metrics Server 설치 (미설치 시)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 애플리케이션 배포
kubectl apply -f kube-manifests/

# LoadBalancer URL 확인 (1-2분 소요)
kubectl get svc jupyter-manager-service
```

### 4. 테스트
```bash
# LoadBalancer URL 저장
export BACKEND_URL=http://$(kubectl get svc jupyter-manager-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Swagger 접속
echo "$BACKEND_URL/docs"

# Swagger에서 POST /users/{user_id}/session 실행
# 예: user_id = testuser1

# 접속
# 브라우저에서 응답의 launch_url 열기
# 예: http://<CLB-DNS>/lab?sessionid=<SESSION_ID>

# 부하 테스트
python3 load-test.py cpu $BACKEND_URL 100 10

# HPA 동작 확인
watch kubectl get hpa,pods -l app=jupyter-manager
```

### 5. 정리
```bash
kubectl delete -f kube-manifests/
```

## 📖 상세 가이드
전체 실습 가이드는 [README.md](README.md)를 참조하세요.

## 🔑 핵심 개념
- **HPA**: CPU/메모리 사용률에 따라 Pod 수 자동 조정
- **Min/Max**: 최소 2개, 최대 10개 Pod
- **스케일 업**: CPU 50% 초과 시
- **스케일 다운**: 5분 안정화 기간 후

## 📞 도움말
문제 발생 시 README.md의 "Step-10: 트러블슈팅" 섹션을 확인하세요.
