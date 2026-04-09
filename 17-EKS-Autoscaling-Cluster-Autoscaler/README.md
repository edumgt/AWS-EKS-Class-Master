# EKS - Cluster Autoscaler

## Step-01: 소개
- Cluster Autoscaler는 `Pending` 상태로 남는 Pod를 감지하면 노드를 늘리고, 반대로 여유 노드가 오래 유지되면 노드를 줄입니다.
- 이 디렉터리는 `eksdemo1` 클러스터에서 `worker node 1개`로 시작한 뒤, `Jupyter Notebook Pod 8개`를 강제로 만들어 `node 4개`까지 scale-up 되는 흐름을 확인하는 실습입니다.

## Step-02: 현재 실습 기준
- 클러스터: `eksdemo1`
- 리전: `ap-northeast-2`
- nodegroup: `ng-eecfef49`
- 시작 상태: `min=1`, `desired=1`
- scale-up 허용 범위: `max=4`

## Step-03: 포함된 파일
- `kube-manifests/01-kubenginx-Deployment-Service.yml`
  기존 간단한 웹앱 예제
- `kube-manifests/02-cluster-autoscaler-autodiscover.yml`
  EKS autodiscover 방식 Cluster Autoscaler 매니페스트
- `kube-manifests/03-jupyter-notebook-scale-test.yml`
  autoscaling 테스트용 Jupyter Notebook 8개 배포 매니페스트
- `iam/cluster-autoscaler-node-role-policy.json`
  node IAM role에 붙일 autoscaler용 정책 예시

## Step-04: NodeGroup IAM 및 ASG 준비
- node IAM role에 autoscaler 정책이 있어야 합니다.
- ASG에는 아래 태그가 있어야 autodiscover가 동작합니다.
  - `k8s.io/cluster-autoscaler/enabled=true`
  - `k8s.io/cluster-autoscaler/eksdemo1=owned`
- nodegroup 최대 노드 수가 `4` 이상이어야 이번 테스트가 성립합니다.

```bash
eksctl get nodegroup --cluster eksdemo1 --region ap-northeast-2

aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names eks-ng-eecfef49-0aceb7d1-6580-a7fd-6de2-2ed37dd10eb0 \
  --region ap-northeast-2
```

## Step-05: Cluster Autoscaler 배포
- 이 저장소에 준비된 매니페스트를 바로 적용합니다.
- EKS `1.34` 기준으로 `cluster-autoscaler:v1.34.1` 이미지를 사용합니다.

```bash
kubectl apply -f kube-manifests/02-cluster-autoscaler-autodiscover.yml

kubectl -n kube-system get deploy,pods -l app=cluster-autoscaler -o wide
kubectl -n kube-system logs deployment/cluster-autoscaler --tail=50
```

## Step-06: Jupyter 8개로 scale-up 테스트
- 아래 매니페스트는 Notebook Pod 8개를 한 번에 만듭니다.
- 각 Pod는 `cpu 500m`, `memory 1Gi`를 요청하므로, node 1개로는 수용할 수 없어 `Pending`이 발생합니다.
- 그 순간 Cluster Autoscaler가 nodegroup을 `1 -> 4`로 확장합니다.

```bash
kubectl apply -f kube-manifests/03-jupyter-notebook-scale-test.yml

kubectl get deploy,rs,pods,svc -l app=ca-jupyter-notebook -o wide
kubectl get nodes -o wide
kubectl -n kube-system logs deployment/cluster-autoscaler --tail=150
kubectl get events --sort-by=.lastTimestamp | tail -n 30
```

## Step-07: 실제로 무엇이 보여야 하나

### 1. 처음에는 Pod 8개가 `Pending`
```bash
kubectl get pods -l app=ca-jupyter-notebook -o wide
```

예상 상태:
- `8/8` 생성됨
- 대부분 `Pending`
- `NODE` 컬럼은 비어 있음

### 2. Cluster Autoscaler 로그에서 scale-up 감지
아래와 비슷한 로그가 보여야 합니다.

```log
Found 27 pods in the cluster: 19 scheduled, 8 unschedulable
Final scale-up plan: [{eks-ng-eecfef49-0aceb7d1-6580-a7fd-6de2-2ed37dd10eb0 1->4 (max: 4)}]
Scale-up: setting group eks-ng-eecfef49-0aceb7d1-6580-a7fd-6de2-2ed37dd10eb0 size to 4
```

### 3. ASG desired capacity 증가 확인
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names eks-ng-eecfef49-0aceb7d1-6580-a7fd-6de2-2ed37dd10eb0 \
  --region ap-northeast-2 \
  --query 'AutoScalingGroups[0].{Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Instances:length(Instances)}'
```

예상 결과:
- `Min=1`
- `Max=4`
- `Desired=4`

### 4. 새 노드가 추가되고 Pod가 배치됨
```bash
kubectl get nodes -o wide
kubectl get pods -l app=ca-jupyter-notebook -o wide
```

예상 흐름:
- 기존 1개 node + 새 node 3개 생성
- 새 node는 잠시 `NotReady` 후 `Ready`
- Jupyter Pod는 `Pending -> ContainerCreating -> Running`

## Step-08: 이번 테스트에서 실제 확인된 예시
- 초기 node 수: `1`
- Jupyter Notebook 배포: `8 replicas`
- Cluster Autoscaler 로그:
  - `8 unschedulable`
  - `Estimated 3 nodes needed`
  - `1->4 (max: 4)` scale-up 실행
- ASG 실제 상태:
  - `DesiredCapacity: 4`
- node 상태:
  - 기존 1개 + 신규 3개 생성 확인

## Step-09: scale-down 실습
- scale-down은 즉시 되지 않고 cooldown이 있어 몇 분 이상 걸릴 수 있습니다.
- 테스트가 끝나면 Jupyter Deployment를 줄이거나 삭제해서 autoscaler가 불필요 노드를 줄이게 할 수 있습니다.

```bash
kubectl scale deployment ca-jupyter-notebook --replicas=1

kubectl get pods -l app=ca-jupyter-notebook -o wide
kubectl get nodes -o wide
kubectl -n kube-system logs deployment/cluster-autoscaler --tail=150
```

또는 전체 삭제:

```bash
kubectl delete -f kube-manifests/03-jupyter-notebook-scale-test.yml
```

## Step-10: 정리
```bash
kubectl delete -f kube-manifests/03-jupyter-notebook-scale-test.yml
kubectl delete -f kube-manifests/02-cluster-autoscaler-autodiscover.yml
```

## 참고
- 지금 테스트는 `Jupyter Pod 8개`를 이용해 일부러 스케줄링 부족을 만드는 방식입니다.
- `1 node`로 시작해야 autoscaler 동작이 가장 잘 보입니다.
- 노드가 `Ready`가 되기 전까지는 Pod가 잠시 `Pending` 또는 `ContainerCreating` 상태로 보이는 것이 정상입니다.
