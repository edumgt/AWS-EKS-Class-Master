# EKS - 수평 Pod 오토스케일링 (HPA) with Jupyter Lab Manager

## Step-01: 소개

### HPA (Horizontal Pod Autoscaler)란?
**수평 Pod 오토스케일러(HPA)**는 CPU 사용률, 메모리 사용률 또는 사용자 정의 메트릭을 기반으로 Pod의 수를 자동으로 조정하는 Kubernetes 기능입니다.

#### HPA 동작 방식
- **스케일 아웃(Scale Out)**: 리소스 사용률이 임계값을 초과하면 Pod 개수를 늘림
- **스케일 인(Scale In)**: 리소스 사용률이 임계값 미만으로 떨어지면 Pod 개수를 줄임
- **Min/Max 설정**: 최소 및 최대 Pod 개수를 지정하여 범위 내에서만 조정

### 이 실습의 목표
본 실습에서는 **FastAPI 기반 Jupyter Lab 관리 시스템**을 구축하고, 사용자 증가에 따라 백엔드 서비스가 자동으로 확장되는 것을 확인합니다.

#### 시스템 구성
```
[사용자] → [LoadBalancer] → [FastAPI Backend (HPA 적용)]
                                    ↓
                          [동적 Jupyter Lab Pods]
```

**주요 기능:**
1. **FastAPI 백엔드**: 사용자 요청을 처리하고 Jupyter Lab Pod를 관리
2. **동적 Pod 생성**: 각 사용자에게 독립적인 Jupyter Lab 환경 제공
3. **HPA 자동 스케일링**: 트래픽 증가 시 백엔드 Pod를 자동으로 확장
4. **부하 테스트**: Python 스크립트로 HPA 동작 검증

---

## Step-02: 사전 준비사항

### 2.1 Metrics Server 설치
HPA가 작동하려면 Metrics Server가 필요합니다.

```bash
# Metrics Server가 이미 설치되어 있는지 확인
kubectl -n kube-system get deployment/metrics-server

# Metrics Server 설치 (설치되지 않은 경우)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 확인
kubectl get deployment metrics-server -n kube-system
```

### 2.2 EKS 클러스터 확인
```bash
# 클러스터 정보 확인
kubectl cluster-info

# 노드 확인
kubectl get nodes

# 현재 네임스페이스 확인
kubectl config view --minify --output 'jsonpath={..namespace}'
```

---

## Step-03: Docker 이미지 빌드 및 ECR 푸시

### 3.1 프로젝트 구조 확인
```
15-EKS-HPA-Horizontal-Pod-Autoscaler/
├── app/
│   ├── main.py              # FastAPI 애플리케이션
│   ├── requirements.txt     # Python 의존성
│   └── Dockerfile          # Docker 이미지 정의
├── kube-manifests/
│   ├── 01-rbac.yml         # ServiceAccount & RBAC
│   ├── 02-backend-deployment.yml  # FastAPI Deployment & Service
│   └── 03-hpa.yml          # HPA 설정
├── build-and-push.sh       # 빌드 및 푸시 스크립트
├── load-test.py            # 부하 테스트 스크립트
└── README.md
```

### 3.2 이미지 빌드 및 ECR 푸시
```bash
# 스크립트에 실행 권한 부여
chmod +x build-and-push.sh
chmod +x mirror-jupyter-image.sh

# AWS 자격 증명 확인
aws sts get-caller-identity

# Jupyter base 이미지 복제
./mirror-jupyter-image.sh

# 이미지 빌드 및 ECR 푸시
./build-and-push.sh

# 또는 환경 변수와 함께 실행
AWS_REGION=ap-northeast-2 IMAGE_TAG=v1.0.0 ./build-and-push.sh
```

스크립트는 다음 작업을 자동으로 수행합니다:
1. ECR 리포지토리 생성 (존재하지 않는 경우)
2. Docker 이미지 빌드
3. ECR에 로그인
4. 이미지를 ECR에 푸시

`mirror-jupyter-image.sh` 는 `jupyter/minimal-notebook:latest` 를 아래 ECR 경로로 복제합니다.

```bash
086015456585.dkr.ecr.ap-northeast-2.amazonaws.com/jupyter-minimal-notebook:latest
```

### 3.3 Deployment YAML 업데이트
기본 Deployment 파일은 현재 EKS 리전 기준 ECR 경로로 설정되어 있습니다:

```bash
# 086015456585.dkr.ecr.ap-northeast-2.amazonaws.com/jupyter-manager:latest
```

필요하면 `kube-manifests/02-backend-deployment.yml`의 image 값을 원하는 태그로 변경합니다.
기본 Jupyter 이미지도 같은 파일의 `JUPYTER_IMAGE` 환경 변수에서 ECR 경로로 설정되어 있습니다.

---

## Step-04: 애플리케이션 배포

### 4.1 RBAC 및 ServiceAccount 생성
FastAPI 백엔드가 Jupyter Lab Pod를 생성/삭제할 수 있도록 권한 부여:

```bash
# RBAC 설정 적용
kubectl apply -f kube-manifests/01-rbac.yml

# 확인
kubectl get serviceaccount jupyter-manager-sa
kubectl get clusterrole jupyter-manager-role
kubectl get clusterrolebinding jupyter-manager-binding
```

### 4.2 FastAPI 백엔드 배포
```bash
# 백엔드 Deployment 및 Service 배포
kubectl apply -f kube-manifests/02-backend-deployment.yml

# Pod 상태 확인
kubectl get pods -l app=jupyter-manager

# Service 확인
kubectl get svc jupyter-manager-service

# LoadBalancer URL 가져오기 (AWS ELB 생성까지 1-2분 소요)
kubectl get svc jupyter-manager-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### 4.3 HPA 설정 적용
```bash
# HPA 생성
kubectl apply -f kube-manifests/03-hpa.yml

# HPA 상태 확인
kubectl get hpa jupyter-manager-hpa

# HPA 상세 정보
kubectl describe hpa jupyter-manager-hpa
```

**HPA 설정 내용:**
- **최소 Pod 수**: 2개
- **최대 Pod 수**: 10개
- **CPU 목표 사용률**: 50%
- **메모리 목표 사용률**: 70%
- **스케일 업**: 최대 100% 증가 (30초마다)
- **스케일 다운**: 최대 50% 감소 (5분 안정화 기간)

---

## Step-05: API 테스트

### 5.1 LoadBalancer URL 저장
```bash
# LoadBalancer URL 환경 변수에 저장
export BACKEND_URL=http://$(kubectl get svc jupyter-manager-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo $BACKEND_URL
```

### 5.2 기본 엔드포인트 테스트
```bash
# 헬스 체크
curl $BACKEND_URL/health

# 메트릭 조회
curl $BACKEND_URL/metrics

# API 문서 (브라우저에서 접속)
echo "$BACKEND_URL/docs"
```

Swagger UI에서는 아래 API를 바로 테스트할 수 있습니다.
- `POST /users/{user_id}/session`
- `GET /session/{session_id}`
- `GET /lab?sessionid=xxxx`

### 5.3 Jupyter Lab 세션 생성
```bash
# 단일 사용자 세션 생성
curl -X POST $BACKEND_URL/session/create \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser1"}'

# 응답 예시:
# {
#   "session_id": "abc123def456",
#   "username": "testuser1",
#   "jupyter_url": "http://svc-jupyter-testuser1-abc123.default.svc.cluster.local:8888/user/abc123def456/lab?token=abc123def456",
#   "access_url": "http://<clb-dns-name>/lab?sessionid=abc123def456",
#   "pod_name": "jupyter-testuser1-abc123def456",
#   "status": "creating"
# }

# 생성된 Jupyter Pod 확인
kubectl get pods -l app=jupyter-lab

# 세션 정보 조회
SESSION_ID="abc123def456"
curl $BACKEND_URL/session/$SESSION_ID

# CLB를 통해 사용자별 Jupyter Lab 접속
echo "$BACKEND_URL/lab?sessionid=$SESSION_ID"

# 모든 세션 목록
curl $BACKEND_URL/sessions
```

브라우저에서는 아래처럼 접근합니다.

```bash
http://<clb-dns-name>/lab?sessionid=<SESSION_ID>
```

Swagger로 생성할 때는:

1. `$BACKEND_URL/docs` 접속
2. `POST /users/{user_id}/session` 선택
3. 예: `user_id = testuser1` 입력 후 `Execute`
4. 응답의 `launch_url` 열기

응답 예시:

```json
{
  "user_id": "testuser1",
  "session_id": "abc123def456",
  "launch_url": "http://<clb-dns-name>/lab?sessionid=abc123def456",
  "status_url": "http://<clb-dns-name>/session/abc123def456",
  "delete_url": "http://<clb-dns-name>/session/abc123def456",
  "status": "creating"
}
```

동작 방식:
- 사용자가 `session/create` 호출
- 또는 Swagger에서 `POST /users/{user_id}/session` 호출
- FastAPI가 사용자 전용 Jupyter Pod와 ClusterIP Service 생성
- CLB 주소의 `/lab?sessionid=...` 요청을 FastAPI가 받음
- FastAPI가 해당 세션의 내부 Jupyter Lab으로 프록시
- 결과적으로 사용자마다 다른 Notebook 세션에 접속

### 5.4 세션 삭제
```bash
# 세션 삭제
curl -X DELETE $BACKEND_URL/session/$SESSION_ID

# Jupyter Pod 삭제 확인
kubectl get pods -l app=jupyter-lab
```

---

## Step-06: HPA 동작 확인

### 6.1 초기 상태 확인
```bash
# 현재 Pod 개수 확인
kubectl get pods -l app=jupyter-manager

# HPA 현재 상태
kubectl get hpa jupyter-manager-hpa

# 출력 예시:
# NAME                   REFERENCE                           TARGETS   MINPODS   MAXPODS   REPLICAS
# jupyter-manager-hpa    Deployment/jupyter-manager-backend  15%/50%   2         10        2
```

### 6.2 Python 부하 테스트 스크립트 사용
```bash
# 부하 테스트 스크립트에 실행 권한 부여
chmod +x load-test.py

# requests 라이브러리 설치 (필요한 경우)
pip3 install requests

# CPU 부하 테스트 (100개 요청, 10개 동시 워커)
python3 load-test.py cpu $BACKEND_URL 100 10

# 또는 더 강한 부하
python3 load-test.py cpu $BACKEND_URL 500 20
```

### 6.3 HPA 스케일 아웃 관찰
새 터미널을 열고 실시간 모니터링:

```bash
# 터미널 1: HPA 모니터링
watch -n 2 kubectl get hpa jupyter-manager-hpa

# 터미널 2: Pod 개수 모니터링
watch -n 2 kubectl get pods -l app=jupyter-manager

# 터미널 3: Pod 리소스 사용률 확인
watch -n 2 kubectl top pods -l app=jupyter-manager
```

**예상 동작:**
1. 부하 테스트 시작 → CPU 사용률 증가
2. CPU 사용률이 50%를 초과하면 HPA가 Pod 추가 시작
3. 최대 10개까지 Pod 증가
4. 부하 종료 → CPU 사용률 감소
5. 5분 안정화 기간 후 Pod 개수를 다시 2개로 축소

### 6.4 Jupyter Lab 세션 기반 부하 테스트
```bash
# 20명의 사용자 세션 동시 생성
python3 load-test.py sessions $BACKEND_URL 20

# 메트릭 모니터링 (60초)
python3 load-test.py monitor $BACKEND_URL 60

# 전체 테스트 (세션 + CPU + 모니터링)
python3 load-test.py all $BACKEND_URL
```

### 6.5 수동 부하 생성 (대안)
```bash
# Apache Bench를 사용한 부하 생성
kubectl run load-generator --rm -it --image=httpd --restart=Never -- \
  ab -n 10000 -c 100 http://jupyter-manager-service/load/generate

# 또는 간단한 while 루프
while true; do
  curl -X POST $BACKEND_URL/load/generate &
done

# 중지: Ctrl+C
```

---

## Step-07: HPA 메트릭 및 동작 분석

### 7.1 HPA 이벤트 확인
```bash
# HPA 이벤트 로그
kubectl describe hpa jupyter-manager-hpa

# 출력 예시:
# Events:
#   Type    Reason             Age   From                       Message
#   ----    ------             ----  ----                       -------
#   Normal  SuccessfulRescale  2m    horizontal-pod-autoscaler  New size: 4; reason: cpu resource utilization (percentage of request) above target
#   Normal  SuccessfulRescale  5m    horizontal-pod-autoscaler  New size: 6; reason: cpu resource utilization (percentage of request) above target
```

### 7.2 Pod 메트릭 확인
```bash
# 모든 Pod의 CPU/메모리 사용률
kubectl top pods -l app=jupyter-manager

# 노드 리소스 사용률
kubectl top nodes
```

### 7.3 HPA Behavior 확인
```bash
# HPA YAML 확인
kubectl get hpa jupyter-manager-hpa -o yaml

# behavior 섹션 확인:
# - scaleUp: 30초마다 최대 100% 증가 가능
# - scaleDown: 60초마다 최대 50% 감소 (5분 안정화)
```

---

## Step-08: 스케일 다운 관찰

### 8.1 쿨다운 기간
- HPA는 스케일 다운 전에 **5분(300초)의 안정화 기간**을 가집니다
- 이는 불필요한 Pod 재시작을 방지하기 위함입니다

### 8.2 스케일 다운 확인
```bash
# 부하 테스트 중지 후
# HPA가 Pod를 줄이는 과정 관찰
watch -n 2 kubectl get hpa,pods -l app=jupyter-manager

# 5분 후 Pod가 최소값(2개)으로 줄어드는 것을 확인
```

---

## Step-09: 고급 HPA 설정 (선택사항)

### 9.1 명령형 HPA 생성
```bash
# 명령줄로 HPA 생성 (간단한 설정)
kubectl autoscale deployment jupyter-manager-backend \
  --cpu-percent=60 \
  --min=2 \
  --max=15

# HPA 삭제
kubectl delete hpa jupyter-manager-backend
```

### 9.2 선언형 HPA (추천)
현재 사용 중인 `03-hpa.yml`은 선언형 방식으로, 다음과 같은 장점이 있습니다:
- **behavior 설정**: 스케일 업/다운 속도 제어
- **여러 메트릭**: CPU, 메모리 동시 모니터링
- **버전 관리**: Git으로 변경 이력 추적
- **재현 가능**: 동일한 환경을 쉽게 재구성

### 9.3 사용자 정의 메트릭 (Advanced)
```yaml
# 예시: 사용자 정의 메트릭 (Prometheus 필요)
metrics:
- type: Pods
  pods:
    metric:
      name: http_requests_per_second
    target:
      type: AverageValue
      averageValue: "1000"
```

---

## Step-10: 트러블슈팅

### 10.1 일반적인 문제

#### HPA가 "unknown" 상태
```bash
# Metrics Server 확인
kubectl get deployment metrics-server -n kube-system

# Metrics Server 로그 확인
kubectl logs -n kube-system deployment/metrics-server

# 해결: Metrics Server 재설치
kubectl delete -n kube-system deployment metrics-server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

#### Pod가 스케일되지 않음
```bash
# Pod에 리소스 요청(requests)이 설정되어 있는지 확인
kubectl get deployment jupyter-manager-backend -o yaml | grep -A 5 resources

# HPA가 올바른 Deployment를 참조하는지 확인
kubectl describe hpa jupyter-manager-hpa
```

#### LoadBalancer URL이 생성되지 않음
```bash
# Service 상태 확인
kubectl describe svc jupyter-manager-service

# EKS 클러스터의 AWS LoadBalancer Controller 확인
kubectl get pods -n kube-system | grep aws-load-balancer

# 해결: NodePort로 임시 접근
kubectl patch svc jupyter-manager-service -p '{"spec":{"type":"NodePort"}}'
kubectl get svc jupyter-manager-service
```

#### Jupyter Pod 생성 실패
```bash
# Pod 로그 확인
kubectl logs -l app=jupyter-manager

# RBAC 권한 확인
kubectl auth can-i create pods --as=system:serviceaccount:default:jupyter-manager-sa

# 해결: RBAC 재적용
kubectl apply -f kube-manifests/01-rbac.yml
```

### 10.2 로그 확인
```bash
# FastAPI 백엔드 로그
kubectl logs -l app=jupyter-manager --tail=50 -f

# 특정 Pod 로그
POD_NAME=$(kubectl get pods -l app=jupyter-manager -o jsonpath='{.items[0].metadata.name}')
kubectl logs $POD_NAME -f

# Jupyter Lab Pod 로그
kubectl logs -l app=jupyter-lab
```

---

## Step-11: 정리 (Clean Up)

### 11.1 리소스 삭제
```bash
# HPA 삭제
kubectl delete -f kube-manifests/03-hpa.yml

# 백엔드 Deployment 및 Service 삭제
kubectl delete -f kube-manifests/02-backend-deployment.yml

# RBAC 삭제
kubectl delete -f kube-manifests/01-rbac.yml

# 실행 중인 모든 Jupyter Lab Pod 삭제
kubectl delete pods -l app=jupyter-lab

# 또는 전체 한 번에 삭제
kubectl delete -f kube-manifests/
```

### 11.2 ECR 이미지 삭제 (선택사항)
```bash
# ECR 리포지토리의 이미지 목록
aws ecr list-images --repository-name jupyter-manager --region us-east-1

# 특정 이미지 삭제
aws ecr batch-delete-image \
  --repository-name jupyter-manager \
  --image-ids imageTag=latest imageTag=v1.0.0 \
  --region us-east-1

# 리포지토리 전체 삭제
aws ecr delete-repository \
  --repository-name jupyter-manager \
  --force \
  --region us-east-1
```

---

## Step-12: 실습 요약 및 핵심 개념

### 12.1 HPA의 주요 특징
1. **자동 스케일링**: 리소스 사용률에 따라 Pod 수를 자동 조정
2. **비용 최적화**: 필요한 만큼만 리소스 사용
3. **고가용성**: 트래픽 증가 시 자동으로 용량 확장
4. **안정화 기간**: 불필요한 스케일링 방지

### 12.2 HPA 구성 요소
```yaml
minReplicas: 2              # 최소 Pod 수
maxReplicas: 10             # 최대 Pod 수
targetCPUUtilization: 50%   # 목표 CPU 사용률
targetMemoryUtilization: 70% # 목표 메모리 사용률
behavior:                    # 스케일링 동작 제어
  scaleUp: ...              # 확장 정책
  scaleDown: ...            # 축소 정책
```

### 12.3 모범 사례
1. **리소스 요청 설정**: Pod에 resources.requests 필수 설정
2. **적절한 메트릭**: CPU뿐만 아니라 메모리, 사용자 정의 메트릭 활용
3. **안정화 기간 조정**: 애플리케이션 특성에 맞게 조정
4. **최소/최대값 설정**: 비용과 성능 균형 고려
5. **모니터링**: Prometheus, Grafana 등으로 HPA 동작 추적

### 12.4 이 실습에서 배운 내용
- ✅ FastAPI 백엔드 개발 및 컨테이너화
- ✅ Kubernetes RBAC를 통한 권한 관리
- ✅ HPA를 사용한 자동 스케일링 구현
- ✅ ECR을 사용한 컨테이너 이미지 관리
- ✅ 동적 Pod 생성 및 관리
- ✅ 부하 테스트를 통한 HPA 검증

---

## Step-13: 추가 학습 자료

### 13.1 다음 단계
- **VPA (Vertical Pod Autoscaler)**: Pod의 리소스 요청/제한 자동 조정
- **Cluster Autoscaler**: 노드 수 자동 조정
- **KEDA**: 이벤트 기반 오토스케일링
- **Prometheus Adapter**: 사용자 정의 메트릭 기반 HPA

### 13.2 참고 링크
- [Kubernetes HPA 공식 문서](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [EKS Best Practices - Autoscaling](https://aws.github.io/aws-eks-best-practices/karpenter/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)

---

## 부록: API 엔드포인트 레퍼런스

### 백엔드 API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | 서비스 상태 확인 |
| GET | `/health` | 헬스 체크 (Kubernetes Probes) |
| GET | `/metrics` | 현재 메트릭 조회 |
| POST | `/session/create` | Jupyter Lab 세션 생성 |
| GET | `/session/{session_id}` | 세션 정보 조회 |
| GET | `/sessions` | 모든 세션 목록 |
| DELETE | `/session/{session_id}` | 세션 삭제 |
| POST | `/load/generate` | CPU 부하 생성 (테스트용) |
| GET | `/pods` | Jupyter Lab Pod 목록 |
| GET | `/docs` | Swagger UI (API 문서) |

---

**💡 실습 완료를 축하합니다!**

이제 Kubernetes HPA를 사용하여 프로덕션 환경에서 자동 스케일링을 구현할 수 있습니다.
      periodSeconds: 15
    - type: Pods
      value: 4
      periodSeconds: 15
    selectPolicy: Max
```
- **참고:** Kubernetes 웹사이트 상단 오른쪽에서 V1.18 문서를 선택하세요.
  -  https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/



## 참고 자료
### Metrics Server 릴리스
- https://github.com/kubernetes-sigs/metrics-server/releases

### Horizontal Pod Autoscaling - 다양한 메트릭 기반 확장
- https://v1-16.docs.kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/
