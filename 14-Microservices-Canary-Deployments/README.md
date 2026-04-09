# NGINX 카나리 배포 실습

간단한 `nginx` 두 버전을 같은 Service 뒤에 두고, 레플리카 비율로 카나리 트래픽 분산을 체험하는 예제입니다.  
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

핵심은 두 Deployment가 모두 같은 `app: nginx-canary-demo` 라벨을 가지므로, Service가 두 버전의 Pod를 함께 바라본다는 점입니다.

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

## Step-04: 현재 트래픽 비율
기본값은 아래와 같습니다.

| Stable replicas | Canary replicas | 예상 비율 |
| --------------- | --------------- | -------- |
| 3 | 1 | Stable 75%, Canary 25% |

더 많은 canary 트래픽을 주고 싶다면 canary 레플리카를 늘리면 됩니다.

```bash
kubectl scale deployment nginx-canary --replicas=2
kubectl get deployment nginx-stable nginx-canary
```

이 경우 예상 비율은 `stable 3 : canary 2` 입니다.

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

여러 번 호출하면 응답 화면에 `NGINX Stable` 또는 `NGINX Canary` 가 번갈아 보입니다. 기본 상태에서는 `stable 3 : canary 1` 이므로 대략 75:25 비율을 기대할 수 있습니다.

## Step-06: 동작 원리
Service selector:

```yaml
selector:
  app: nginx-canary-demo
```

Stable Pod와 Canary Pod가 모두 이 라벨을 가지므로, Kubernetes Service가 두 버전으로 트래픽을 분산합니다. 이 예제에서는 별도 서비스메시 없이 레플리카 수로 가장 단순하게 카나리 개념을 실습합니다.

## Step-07: 정리
```bash
kubectl delete -f kube-manifests/03-UserManagement-NodePort-Service.yml
kubectl delete -f kube-manifests/04-NotificationMicroservice-Deployment.yml
kubectl delete -f kube-manifests/02-UserManagementMicroservice-Deployment.yml
```
