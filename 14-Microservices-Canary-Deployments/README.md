# NGINX 카나리 배포 실습

간단한 `nginx` 두 버전을 배포하고, replica 비율에 따라 외부 접속 비율이 달라지도록 구성한 예제입니다.  
이 버전은 EKS에서 `Service type=LoadBalancer`로 외부 노출해 `CLB` 실습을 하는 흐름입니다.

## Step-01: 클러스터 준비
```bash
eksctl create cluster --name=eksdemo1 \
  --region=ap-northeast-2 \
  --zones=ap-northeast-2a,ap-northeast-2b \
  --nodes=2 \
  --node-private-networking
```

## Step-02: 실습 구조
- `02-UserManagementMicroservice-Deployment.yml`: stable NGINX 배포
- `04-NotificationMicroservice-Deployment.yml`: canary NGINX 배포
- `03-UserManagement-NodePort-Service.yml`: stable/canary 공용 `LoadBalancer` Service

핵심은 stable/canary 두 Deployment를 모두 유지하고, Service는 `app: nginx-canary-demo` 라벨만 기준으로 두 버전의 Pod를 함께 바라보게 하는 점입니다. 따라서 replica 비율을 바꾸면 접속 비율도 함께 달라집니다.

참고:
- AWS 공식 문서 기준으로 legacy AWS Service Controller 경로에서는 `type: LoadBalancer` 서비스가 기본적으로 `CLB`를 생성합니다.
- 다만 클러스터가 `AWS Load Balancer Controller` 또는 `EKS Auto Mode`에 의해 다르게 구성되어 있으면 `NLB`로 생성될 수 있습니다.
- 이 실습은 `CLB`가 생성되는 일반적인 legacy EKS 서비스 노출 흐름을 기준으로 작성했습니다.

## Step-03: 매니페스트 배포
```bash
kubectl apply -f kube-manifests/02-UserManagementMicroservice-Deployment.yml
kubectl apply -f kube-manifests/04-NotificationMicroservice-Deployment.yml
kubectl apply -f kube-manifests/03-UserManagement-NodePort-Service.yml
```

## Step-04: 현재 접속 대상
기본값은 아래와 같습니다.

| Stable replicas | Canary replicas | 예상 접속 비율 |
| --------------- | --------------- | ------------- |
| 3 | 1 | Stable 75%, Canary 25% |

더 많은 canary 비율을 주고 싶다면 canary 레플리카를 늘리면 됩니다.

```bash
kubectl scale deployment nginx-canary --replicas=2
kubectl get deployment nginx-stable nginx-canary
```

이 경우 예상 비율은 `stable 3 : canary 2` 입니다.

예를 들어 아래처럼 바꿀 수 있습니다.

```bash
kubectl scale deployment nginx-stable --replicas=4
kubectl scale deployment nginx-canary --replicas=1
```

이 경우 예상 비율은 `stable 80%, canary 20%` 입니다.

## Step-05: 확인
```bash
kubectl get deploy,svc,pod
kubectl get svc nginx-canary-clb-service
```

외부 접속 주소 확인:
```bash
kubectl get svc nginx-canary-clb-service
```

`EXTERNAL-IP` 또는 `hostname` 이 할당되면 다음처럼 테스트합니다.

```bash
curl http://<clb-dns-name>
```

여러 번 호출하면 응답이 `NGINX Stable` 과 `NGINX Canary` 사이에서 비율에 맞춰 섞여 보여야 합니다.

## Step-06: 동작 원리
Service selector:

```yaml
selector:
  app: nginx-canary-demo
```

Stable Pod와 Canary Pod가 모두 `app: nginx-canary-demo` 라벨을 가지므로, Service는 두 버전의 Pod를 함께 선택합니다. Kubernetes Service는 선택된 Pod들로 트래픽을 분산하므로, replica 비율을 조정하면 canary 비율도 함께 바뀝니다.

## Step-07: 로그 임계치 기반 전환 테스트
`scripts/demo-log-threshold-shift.sh` 는 아래 순서로 동작합니다.

1. Service를 먼저 `stable` 만 바라보게 패치
2. 클러스터 내부에서 가상 웹 요청 12회를 생성
3. stable NGINX access log를 집계
4. 로그 수가 10회를 초과하면 Service를 `canary` 로 전환
5. 전환 후 추가 요청을 보내 canary 로그가 쌓이는지 확인

실행:

```bash
chmod +x scripts/demo-log-threshold-shift.sh
./scripts/demo-log-threshold-shift.sh
```

환경 변수로 임계치와 요청 수를 바꿀 수 있습니다.

```bash
THRESHOLD=5 REQUEST_COUNT=8 VERIFY_COUNT=2 ./scripts/demo-log-threshold-shift.sh
```

현재 스크립트는 `stable -> canary` 전환을 보여주는 데모입니다. 전환 후에는 다음 명령으로 selector 상태를 확인할 수 있습니다.

```bash
kubectl get svc nginx-canary-clb-service -o jsonpath='{.spec.selector}'
```

NGINX 응답 페이지에는 Pod 이름도 같이 표시되므로, 어떤 Pod가 응답했는지 확인하기 쉽습니다.

## Step-08: 정리
```bash
kubectl delete -f kube-manifests/03-UserManagement-NodePort-Service.yml
kubectl delete -f kube-manifests/04-NotificationMicroservice-Deployment.yml
kubectl delete -f kube-manifests/02-UserManagementMicroservice-Deployment.yml
```
