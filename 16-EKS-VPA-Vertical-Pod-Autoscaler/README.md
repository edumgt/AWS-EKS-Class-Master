# EKS - 수직 Pod 오토스케일링 (VPA)

## Step-01: 소개
- Kubernetes VPA는 Pod의 CPU/메모리 `requests` 값을 관찰 기반으로 추천하고, 필요 시 새 Pod를 재생성하면서 반영합니다.
- 이 실습은 `LoadBalancer` Service를 사용해 EKS에서 외부 주소로 바로 접속하면서 VPA 동작을 확인하는 흐름입니다.

## Step-02: 사전 준비
- `metrics-server`가 설치되어 있어야 합니다.
- VPA 컨트롤러가 설치되어 있어야 합니다.

```bash
kubectl get pods -n kube-system | grep -E 'metrics-server|vpa'
```

## Step-03: VPA 설치

```bash
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler/
./hack/vpa-down.sh
./hack/vpa-up.sh
kubectl get pods -n kube-system
```

## Step-04: 애플리케이션 배포
- 기본 실습값은 `replicas: 2` 입니다.
- Service는 `type: LoadBalancer` 로 바꿔 두었기 때문에 EKS에서 외부 ELB 주소가 생성됩니다.

```bash
cd /home/AWS-EKS-Class-Master/16-EKS-VPA-Vertical-Pod-Autoscaler
kubectl apply -f kube-manifests/01-VPA-DemoApplication.yml
kubectl get deploy,pod,svc
```

외부 주소 확인:

```bash
kubectl get svc vpa-demo-service-nginx
kubectl get svc vpa-demo-service-nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

브라우저 또는 curl 확인:

```bash
curl http://<CLB-DNS-NAME>
```

참고:
- 일반 EKS 기본 service controller 기준이면 CLB 형태로 생성될 수 있습니다.
- 클러스터 설정에 따라 NLB로 만들어질 수도 있으니, 실습에서는 "외부 ELB 주소" 기준으로 보면 됩니다.

## Step-05: VPA 배포
- `updateMode: Auto` 를 명시해 두었습니다.

```bash
kubectl apply -f kube-manifests/02-VPA-Manifest.yml
kubectl get vpa
kubectl describe vpa kubengix-vpa
```

## Step-06: 부하 생성
- 내부 Service DNS 기준으로 부하를 넣는 게 가장 안정적입니다.
- 외부 CLB 주소로 접속 확인은 별도, 실제 VPA 관찰용 부하는 클러스터 내부에서 넣습니다.
- 실습 편의를 위해 `scripts/run-vpa-load.sh` 와 `scripts/watch-vpa-resources.sh` 를 추가했습니다.

```bash
kubectl get pods -w
```

```bash
kubectl run apache-bench --rm -it --restart=Never --image=httpd \
  -- ab -n 200000 -c 500 http://vpa-demo-service-nginx.default.svc.cluster.local/
```

원하면 2개 이상 동시에 실행:

```bash
kubectl run apache-bench-2 --rm -it --restart=Never --image=httpd \
  -- ab -n 200000 -c 500 http://vpa-demo-service-nginx.default.svc.cluster.local/
```

```bash
kubectl run apache-bench-3 --rm -it --restart=Never --image=httpd \
  -- ab -n 200000 -c 500 http://vpa-demo-service-nginx.default.svc.cluster.local/
```

스크립트 사용:

```bash
cd /home/AWS-EKS-Class-Master/16-EKS-VPA-Vertical-Pod-Autoscaler
chmod +x scripts/*.sh
./scripts/run-vpa-load.sh
```

옵션 예시:

```bash
WORKERS=3 REQUESTS=150000 CONCURRENCY=300 ./scripts/run-vpa-load.sh
```

## Step-07: VPA 추천값 확인

```bash
kubectl describe vpa kubengix-vpa
```

여기서 보통 아래 항목을 봅니다.
- `Recommendation`
- `Target`
- `Lower Bound`
- `Upper Bound`

Pod 리소스 변경 상태와 VPA 추천값을 같이 보기:

```bash
cd /home/AWS-EKS-Class-Master/16-EKS-VPA-Vertical-Pod-Autoscaler
chmod +x scripts/*.sh
./scripts/watch-vpa-resources.sh
```

이 스크립트는 아래를 반복 출력합니다.
- LoadBalancer 외부 주소
- Deployment ready/desired 수
- 현재 Pod 목록
- 각 Pod의 `requests` / `limits`
- `kubectl describe vpa` 의 Recommendation 섹션

갱신 주기 변경 예시:

```bash
INTERVAL=3 ./scripts/watch-vpa-resources.sh
```

## Step-08: 핵심 실습 1 - Pod가 2개 이상일 때

현재 매니페스트는 `replicas: 2` 이므로 바로 이 케이스입니다.

```bash
kubectl get deploy vpa-demo-deployment
kubectl get pods -l app=vpa-nginx -w
kubectl describe vpa kubengix-vpa
```

추천 실습 순서:

```bash
./scripts/watch-vpa-resources.sh
```

새 터미널:

```bash
WORKERS=2 REQUESTS=200000 CONCURRENCY=500 ./scripts/run-vpa-load.sh
```

### 기대 동작
1. 부하가 충분히 들어가면 VPA가 더 큰 CPU/메모리 `requests` 를 추천합니다.
2. `updateMode: Auto` 이면 VPA Updater가 기존 Pod 일부를 종료합니다.
3. Deployment가 새 Pod를 생성하면서 추천된 CPU/메모리 `requests` 가 반영됩니다.
4. Pod가 2개 이상이므로 서비스는 완전히 끊기지 않고 순차 재기동되는 모습을 볼 수 있습니다.

### 구체적인 관찰 예시

기존 Pod 확인:

```bash
kubectl get pods -l app=vpa-nginx
kubectl describe pod <pod-name> | grep -A5 Requests
```

초기값 예시:

```text
Requests:
  cpu:     5m
  memory:  5Mi
```

부하 이후 VPA 추천 확인:

```bash
kubectl describe vpa kubengix-vpa
```

예시로 이런 추천이 나올 수 있습니다.

```text
Target:
  cpu:     120m
  memory:  90Mi
```

이후 새로 뜬 Pod 확인:

```bash
kubectl describe pod <recently-recreated-pod> | grep -A5 Requests
```

예시:

```text
Requests:
  cpu:     120m
  memory:  90Mi
```

즉, `Pod 2개 이상` 이면 VPA Updater가 하나를 내려도 나머지 Pod가 계속 서비스하고, 새 Pod가 추천값을 반영해 올라옵니다.

## Step-09: 핵심 실습 2 - Pod가 1개뿐일 때

이제 같은 Deployment를 1개 Pod만 남기고 비교합니다.

```bash
kubectl scale deployment vpa-demo-deployment --replicas=1
kubectl get deploy,pods -l app=vpa-nginx
```

다시 부하를 줍니다.

```bash
kubectl run apache-bench-single --rm -it --restart=Never --image=httpd \
  -- ab -n 200000 -c 500 http://vpa-demo-service-nginx.default.svc.cluster.local/
```

VPA 추천 확인:

```bash
kubectl describe vpa kubengix-vpa
```

### 기대 동작
1. VPA는 여전히 더 큰 CPU/메모리를 추천할 수 있습니다.
2. 하지만 Pod가 1개뿐이면 Updater가 그 Pod를 자동으로 내려버리기 어렵습니다.
3. 따라서 추천값은 보이지만, 기존 단일 Pod는 그대로 살아 있고 새 요청값이 바로 적용되지 않을 수 있습니다.

### 구체적인 예시

현재 단일 Pod 요청값:

```bash
kubectl describe pod <single-pod-name> | grep -A5 Requests
```

예시:

```text
Requests:
  cpu:     5m
  memory:  5Mi
```

VPA 추천은 커졌는데:

```text
Target:
  cpu:     140m
  memory:  110Mi
```

단일 Pod는 그대로일 수 있습니다.

```bash
kubectl describe pod <single-pod-name> | grep -A5 Requests
```

여전히:

```text
Requests:
  cpu:     5m
  memory:  5Mi
```

이때 수동 삭제:

```bash
kubectl delete pod <single-pod-name>
```

그러면 Deployment가 새 Pod를 만들고, 그 새 Pod는 VPA 추천값을 반영한 상태로 시작될 수 있습니다.

확인:

```bash
kubectl get pods -l app=vpa-nginx
kubectl describe pod <new-pod-name> | grep -A5 Requests
```

예시:

```text
Requests:
  cpu:     140m
  memory:  110Mi
```

이 케이스도 같은 방식으로 보면 편합니다.

터미널 1:

```bash
INTERVAL=3 ./scripts/watch-vpa-resources.sh
```

터미널 2:

```bash
WORKERS=1 REQUESTS=200000 CONCURRENCY=500 ./scripts/run-vpa-load.sh
```

## Step-10: 외부 CLB 주소 기반 확인 포인트

외부 주소는 단순 접속 확인용으로 이렇게 씁니다.

```bash
export VPA_LB=$(kubectl get svc vpa-demo-service-nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo $VPA_LB
curl http://$VPA_LB
```

정리하면:
- 외부 ELB 주소: 브라우저 접속과 데모 확인
- 내부 Service DNS: VPA 관찰용 대량 부하 생성

## Step-11: 왜 이런 차이가 나는가
1. VPA는 새 Pod가 만들어질 때 추천 `requests` 를 주입하는 방식으로 적용됩니다.
2. Deployment에 Pod가 2개 이상이면 하나를 재시작해도 서비스 연속성이 유지됩니다.
3. Pod가 1개면 자동 재시작 시 순간 서비스 중단 위험이 있으므로, 바로 교체되지 않거나 더 보수적으로 보일 수 있습니다.

## Step-12: 정리

```bash
kubectl delete -f kube-manifests/
```
