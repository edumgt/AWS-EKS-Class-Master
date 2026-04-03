# EKS 클러스터 및 노드 그룹 생성

## Step-00: 소개
- EKS 핵심 객체 이해
  - 컨트롤 플레인
  - 워커 노드 및 노드 그룹
  - Fargate 프로파일
  - VPC
- EKS 클러스터 생성
- EKS 클러스터와 IAM OIDC 제공자 연결
- EKS 노드 그룹 생성
- 클러스터, 노드 그룹, EC2 인스턴스, IAM 정책 및 노드 그룹 확인


## Step-01: eksctl로 EKS 클러스터 생성
- 클러스터 컨트롤 플레인 생성에 15~20분 소요됩니다.
```
# 클러스터 생성
eksctl create cluster --name=eksdemo2 \
                      --region=ap-northeast-2 \
                      --zones=ap-northeast-2a,ap-northeast-2b \
                      --without-nodegroup 

# 클러스터 목록 확인
eksctl get cluster                  
```


## Step-02: EKS 클러스터용 IAM OIDC 제공자 생성 및 연결
- EKS 클러스터에서 Kubernetes 서비스 계정용 AWS IAM 역할을 사용하려면 OIDC ID 제공자를 생성하고 연결해야 합니다.
- `eksctl`로 아래 명령을 실행합니다.
- 최신 eksctl 버전을 사용하세요(현재 최신은 `0.21.0`).
```                   
# 템플릿
eksctl utils associate-iam-oidc-provider \
    --region region-code \
    --cluster <cluter-name> \
    --approve

# 리전 및 클러스터 이름 교체
eksctl utils associate-iam-oidc-provider \
    --region us-east-1 \
    --cluster eksdemo1 \
    --approve
```



## Step-03: EC2 키 페어 생성
- `kube-demo`라는 이름으로 새 EC2 키 페어를 생성합니다.
- 이 키 페어는 EKS 노드 그룹 생성 시 사용합니다.
- 터미널에서 EKS 워커 노드에 로그인하는 데 필요합니다.

## Step-04: 퍼블릭 서브넷에 추가 애드온을 포함한 노드 그룹 생성
- 이 애드온들은 노드 그룹 역할에 필요한 IAM 정책을 자동으로 생성해 줍니다.
```
# 퍼블릭 노드 그룹 생성
eksctl create nodegroup --cluster=eksdemo2 \
                        --region=ap-northeast-2 \
                        --name=eksdemo2-ng-public2 \
                        --node-type=t3.medium \
                        --nodes=1 \
                        --nodes-min=1 \
                        --nodes-max=2 \
                        --node-volume-size=20 \
                        --ssh-access \
                        --ssh-public-key=kube-demo \
                        --managed \
                        --asg-access \
                        --external-dns-access \
                        --full-ecr-access \
                        --appmesh-access \
                        --alb-ingress-access 
```
---
```
2026-02-05 10:19:40 [ℹ]  1 error(s) occurred and nodegroups haven't been created properly, you may wish to check CloudFormation console
2026-02-05 10:19:40 [ℹ]  to cleanup resources, run 'eksctl delete nodegroup --region=ap-northeast-2 --cluster=eksdemo3 --name=<name>' for each of the failed nodegroup
2026-02-05 10:19:40 [✖]  waiter state transitioned to Failure
Error: failed to create nodegroups for cluster "eksdemo3"
```
---
![alt text](image.png)
```
위의 에러로 CloudFormation 에서 조회

이 AWS::EKS::Nodegroup 리소스가 CREATE_FAILED 상태입니다

Resource handler returned message: "Volume of size 10GB is smaller than snapshot 'snap-00d5f67a6dbba0b5f', expect size >= 20GB (Service: Eks, Status Code: 400, Request ID: 976c48ac-3ee4-4bc9-9e04-b9658090dc57) (SDK Attempt Count: 1)" (RequestToken: a0f38587-31f9-4ffe-18e4-9accbc11083b, HandlerErrorCode: InvalidRequest)
```
---
### console 에서 노드 IAM 역할 권한 보기
![alt text](image-1.png)


## Step-05: 클러스터 및 노드 확인

### 노드 그룹 서브넷 확인 (EC2 인스턴스가 퍼블릭 서브넷인지 확인)
- 노드 그룹 서브넷이 퍼블릭 서브넷에 생성됐는지 확인합니다.
  - Services -> EKS -> eksdemo -> eksdemo1-ng1-public 이동
  - **Details** 탭에서 Associated subnet 클릭
  - **Route Table** 탭 클릭
  - 인터넷 게이트웨이 경로(0.0.0.0/0 -> igw-xxxxxxxx)가 있어야 합니다.

### EKS 관리 콘솔에서 클러스터와 노드 그룹 확인
- Services -> Elastic Kubernetes Service -> eksdemo1 이동

### 워커 노드 목록 확인
```
# EKS 클러스터 목록
eksctl get cluster

# 클러스터 내 노드 그룹 목록
eksctl get nodegroup --cluster=<clusterName>

# 현재 Kubernetes 클러스터의 노드 목록
kubectl get nodes -o wide

# kubectl 컨텍스트가 새 클러스터로 자동 변경되었는지 확인
kubectl config view --minify
```

### 워커 노드 IAM 역할 및 정책 목록 확인
- Services -> EC2 -> Worker Nodes 이동
- EC2 워커 노드에 연결된 **IAM Role** 클릭

### 워커 노드 보안 그룹 확인
- Services -> EC2 -> Worker Nodes 이동
- `remote`가 포함된 이름의 EC2 인스턴스 **Security Group** 클릭

### CloudFormation 스택 확인
- 컨트롤 플레인 스택 및 이벤트 확인
- 노드 그룹 스택 및 이벤트 확인

### 키 페어 kube-demo로 워커 노드 로그인
- 워커 노드 로그인
```
# Mac 또는 Linux 또는 Windows10
ssh -i kube-demo.pem ec2-user@<Public-IP-of-Worker-Node>

# Windows 7
Use putty
```

## Step-06: 워커 노드 보안 그룹에 모든 트래픽 허용
- 워커 노드 보안 그룹에서 `All Traffic`을 허용해야 합니다.

## 추가 참고 자료
- https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html
- https://docs.aws.amazon.com/eks/latest/userguide/create-service-account-iam-policy-and-role.html

---

## Step-07: Calico CNI 설치 (VPC CNI → Calico 교체)

EKS의 기본 네트워크 플러그인은 **Amazon VPC CNI**입니다. Calico는 보다 유연한 네트워크 정책(NetworkPolicy)과 멀티 클라우드 CNI 지원이 필요할 때 VPC CNI 대신 사용합니다.

> **참고:** Calico를 기본 CNI 플러그인으로 사용하려면 클러스터 생성 시 노드 그룹 없이 먼저 컨트롤플레인만 생성해야 합니다.

### Step-07-01: Calico CNI 클러스터 생성 (노드 그룹 없이)
```bash
# 방법 1: 클러스터 설정 YAML 사용 (cluster-calico.yaml 참고)
eksctl create cluster -f cluster-calico.yaml

# 방법 2: CLI 명령어 직접 사용
eksctl create cluster --name=eksdemo-calico \
                      --region=ap-northeast-2 \
                      --zones=ap-northeast-2a,ap-northeast-2b \
                      --without-nodegroup

# OIDC 제공자 연결
eksctl utils associate-iam-oidc-provider \
    --region ap-northeast-2 \
    --cluster eksdemo-calico \
    --approve
```

### Step-07-02: 기본 VPC CNI(aws-node) 제거
```bash
# aws-node DaemonSet 삭제 (VPC CNI 비활성화)
kubectl delete daemonset -n kube-system aws-node
```

### Step-07-03: Calico Tigera Operator 설치
```bash
# Tigera Operator 설치 (v3.29.0 기준, 최신 버전 확인 권장)
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/tigera-operator.yaml

# 설치 확인
kubectl get pods -n tigera-operator
```

### Step-07-04: Calico Installation CR 적용
```bash
# Calico Installation 커스텀 리소스 적용
kubectl create -f kube-manifests/calico-installation.yaml

# calico-system 네임스페이스의 Pod 상태 확인 (모두 Running 상태가 될 때까지 대기)
watch kubectl get pods -n calico-system
```

### Step-07-05: 노드 그룹 생성
```bash
# Calico 설치 완료 후 노드 그룹 생성
eksctl create nodegroup --cluster=eksdemo-calico \
                        --region=ap-northeast-2 \
                        --name=eksdemo-calico-ng-public \
                        --node-type=t3.medium \
                        --nodes=2 \
                        --nodes-min=1 \
                        --nodes-max=3 \
                        --node-volume-size=20 \
                        --ssh-access \
                        --ssh-public-key=kube-demo \
                        --managed \
                        --asg-access \
                        --external-dns-access \
                        --full-ecr-access \
                        --appmesh-access \
                        --alb-ingress-access
```

### Step-07-06: Calico CNI 동작 확인
```bash
# 노드 확인 (Ready 상태)
kubectl get nodes -o wide

# Calico 파드 확인
kubectl get pods -n calico-system

# Calico API 서버 확인
kubectl get pods -n calico-apiserver

# Calico 노드 상태 확인 (calicoctl 사용)
kubectl exec -n calico-system \
  $(kubectl get pod -n calico-system -l k8s-app=calico-node -o jsonpath='{.items[0].metadata.name}') \
  -- calico-node -bird-ready -felix-ready
```

### Calico CNI 특징 (VPC CNI/Flannel 비교)

| 항목 | Amazon VPC CNI (기본) | Calico CNI |
|------|----------------------|------------|
| Pod IP 할당 | VPC IP 1개/Pod (ENI 기반) | Calico IPAM (overlay: VXLAN/BGP) |
| 노드당 Pod 수 제한 | 인스턴스 타입 ENI 개수에 비례 (t3.medium: 17개) | 기본값 110개 (maxPods 설정 가능) |
| 네트워크 정책 | 별도 Calico Policy Engine 필요 | 기본 내장 (`NetworkPolicy` 완전 지원) |
| 멀티클라우드 지원 | AWS 전용 | AWS/GCP/Azure/온프레미스 동일 CNI |
| eBPF 데이터플레인 | 미지원 | 지원 (고성능 네트워킹) |

> **NetworkPolicy 예시 (Calico)**
> ```yaml
> apiVersion: networking.k8s.io/v1
> kind: NetworkPolicy
> metadata:
>   name: allow-frontend-to-backend
>   namespace: default
> spec:
>   podSelector:
>     matchLabels:
>       app: backend
>   policyTypes:
>     - Ingress
>   ingress:
>     - from:
>         - podSelector:
>             matchLabels:
>               app: frontend
>       ports:
>         - protocol: TCP
>           port: 8080
> ```

### Step-07-07: 정리
```bash
# 노드 그룹 삭제
eksctl delete nodegroup --cluster=eksdemo-calico --name=eksdemo-calico-ng-public --region=ap-northeast-2

# 클러스터 삭제
eksctl delete cluster --name=eksdemo-calico --region=ap-northeast-2
```

---

## Step-08: Kubernetes Dashboard v3.x 설치 (Helm 방식)

Kubernetes Dashboard v3.x는 최신 UI와 향상된 보안 모델을 제공합니다. 기존 v2.x와 달리 **Kong Gateway**를 통해 서비스되며 Helm으로 설치합니다.

### Step-08-01: Helm으로 kubernetes-dashboard 설치
```bash
# kubernetes-dashboard Helm 레포지토리 추가
helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
helm repo update

# Dashboard 설치 (v3.x 최신 버전)
helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard \
  --create-namespace \
  --namespace kubernetes-dashboard

# 설치 확인
kubectl -n kubernetes-dashboard get pods
kubectl -n kubernetes-dashboard get svc
```

### Step-08-02: 관리자 ServiceAccount 생성
```bash
# 관리자 ServiceAccount 및 ClusterRoleBinding 적용
kubectl apply -f kube-manifests/dashboard-admin-user.yaml
```

### Step-08-03: Bearer 토큰 발급
```bash
# 임시 토큰 발급 (유효기간: 기본 1시간)
kubectl -n kubernetes-dashboard create token admin-user

# 장기 토큰이 필요한 경우 Secret 생성 (학습/개발 환경 전용)
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: admin-user-token
  namespace: kubernetes-dashboard
  annotations:
    kubernetes.io/service-account.name: admin-user
type: kubernetes.io/service-account-token
EOF

kubectl -n kubernetes-dashboard get secret admin-user-token -o jsonpath='{.data.token}' | base64 -d
```

### Step-08-04: 로컬에서 Dashboard 접속 (포트 포워딩)
```bash
# Kong 프록시 포트 포워딩 (v3.x에서는 kong-proxy 서비스 사용)
kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 8443:443

# 브라우저에서 접속 (자체 서명 인증서이므로 브라우저 경고 무시)
# https://localhost:8443
```

> **중요:** 발급된 Bearer 토큰을 Dashboard 로그인 화면에 입력하면 접속됩니다.

### Step-08-05: Dashboard 주요 기능 (v3.x)

| 기능 | 설명 |
|------|------|
| 워크로드 개요 | Deployment, Pod, ReplicaSet, StatefulSet 시각화 |
| 실시간 로그 | 컨테이너 로그 스트리밍 뷰어 |
| 리소스 편집 | YAML 직접 편집 및 적용 |
| 네임스페이스 전환 | 멀티 네임스페이스 지원 |
| 메트릭 표시 | metrics-server 연동 시 CPU/메모리 그래프 표시 |
| 다크 모드 | 밝은/어두운 테마 선택 지원 |

### Step-08-06: Dashboard 버전 확인 및 업그레이드
```bash
# 현재 설치된 차트 버전 확인
helm list -n kubernetes-dashboard

# 최신 버전으로 업그레이드
helm repo update
helm upgrade kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard \
  --namespace kubernetes-dashboard
```

### Step-08-07: 정리
```bash
# Dashboard 삭제
helm uninstall kubernetes-dashboard --namespace kubernetes-dashboard
kubectl delete namespace kubernetes-dashboard
kubectl delete clusterrolebinding admin-user
```

### Kubernetes Dashboard 버전 비교

| 항목 | v2.x (구버전) | v3.x (최신) |
|------|--------------|------------|
| 설치 방식 | kubectl apply -f (단일 YAML) | Helm Chart |
| 게이트웨이 | 내장 HTTP 서버 | Kong Gateway |
| 인증 | 토큰/kubeconfig, skip 옵션 있음 | 토큰/kubeconfig (skip 옵션 제거됨) |
| UI 프레임워크 | Angular | Angular (리팩터링) |
| 메트릭 연동 | metrics-server 연동 | metrics-server 연동 |
| 최소 쿠버네티스 버전 | 1.19+ | 1.25+ |

- **공식 문서:** https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/
- **Helm Chart:** https://artifacthub.io/packages/helm/k8s-dashboard/kubernetes-dashboard
- **GitHub:** https://github.com/kubernetes/dashboard
