# AWS, kubectl, eksctl CLI 설치

## Step-00: 소개
- AWS CLI 설치
- kubectl CLI 설치
- eksctl CLI 설치

## Step-01: AWS CLI 설치
- 참고-1: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html
- 참고-2: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html

### Step-01-01: Mac - AWS CLI 설치 및 구성
- 아래 두 개 명령으로 바이너리를 다운로드하고 커맨드 라인에서 설치합니다.
```
# 바이너리 다운로드
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"

# 바이너리 설치
sudo installer -pkg ./AWSCLIV2.pkg -target /
```
- 설치 확인
```
aws --version
aws-cli/2.0.7 Python/3.7.4 Darwin/19.4.0 botocore/2.0.0dev11

which aws
```
- 참고: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-mac.html

### Step-01-02: Windows 10 - AWS CLI 설치 및 구성
- AWS CLI 버전 2는 Windows XP 이상에서 지원됩니다.
- AWS CLI 버전 2는 64비트 Windows만 지원합니다.
- 바이너리 다운로드: https://awscli.amazonaws.com/AWSCLIV2.msi
- 다운로드한 바이너리 설치(일반 Windows 설치)
```
aws --version
aws-cli/2.0.8 Python/3.7.5 Windows/10 botocore/2.0.0dev12
```
- 참고: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html

### Step-01-03: 보안 자격 증명을 사용해 AWS CLI 구성
- AWS Management Console --> Services --> IAM으로 이동
- IAM 사용자 선택: kalyan
- **중요:** 루트 사용자가 아닌 IAM 사용자로만 **보안 자격 증명**을 생성하세요. (강력히 비권장)
- **Security credentials** 탭 클릭
- **Create access key** 클릭
- Access ID와 Secret access key 복사
- 커맨드 라인에서 필요한 정보를 입력
```
aws configure
AWS Access Key ID [None]: xxx
AWS Secret Access Key [None]: xxx
Default region name [None]: us-east-1
Default output format [None]: json
```
- 위 설정 이후 AWS CLI가 정상 동작하는지 테스트
```
aws ec2 describe-vpcs
```

## Step-02: kubectl CLI 설치
- **중요:** EKS용 kubectl 바이너리는 Amazon에서 제공하는 버전(**Amazon EKS-vended kubectl binary**)을 사용하는 것을 권장합니다.
- EKS 클러스터 버전에 맞는 정확한 kubectl 클라이언트 버전을 받을 수 있습니다. 아래 문서 링크를 참고해 바이너리를 다운로드하세요.
- 참고: https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html

### Step-02-01: Mac - kubectl 설치 및 구성
- 여기서는 kubectl 1.16.8 버전을 사용합니다. (EKS 클러스터 버전에 따라 달라질 수 있음)

```
# 패키지 다운로드
mkdir kubectlbinary
cd kubectlbinary
curl -o kubectl https://amazon-eks.s3.us-west-2.amazonaws.com/1.16.8/2020-04-16/bin/darwin/amd64/kubectl

# 실행 권한 부여
chmod +x ./kubectl

# 사용자 홈 디렉터리에 복사해 PATH 설정
mkdir -p $HOME/bin && cp ./kubectl $HOME/bin/kubectl && export PATH=$PATH:$HOME/bin
echo 'export PATH=$PATH:$HOME/bin' >> ~/.bash_profile

# kubectl 버전 확인
kubectl version --short --client
Output: Client Version: v1.16.8-eks-e16311
```


### Step-02-02: Windows 10 - kubectl 설치 및 구성
- Windows 10에 kubectl 설치
```
mkdir kubectlbinary
cd kubectlbinary
curl -o kubectl.exe https://amazon-eks.s3.us-west-2.amazonaws.com/1.16.8/2020-04-16/bin/windows/amd64/kubectl.exe
```
- 시스템 **Path** 환경 변수 업데이트
```
C:\Users\KALYAN\Documents\kubectlbinary
```
- kubectl 클라이언트 버전 확인
```
kubectl version --short --client
kubectl version --client
```

## Step-03: eksctl CLI 설치
### Step-03-01: Mac에서 eksctl 설치
```
# MacOS에 Homebrew 설치
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"

# Weaveworks Homebrew 탭 추가
brew tap weaveworks/tap

# Weaveworks Homebrew 탭에서 eksctl 설치
brew install weaveworks/tap/eksctl

# eksctl 버전 확인
eksctl version
```

---
# WSL Ubuntu에서 `kubectl` / `eksctl` 설치 & EKS 연결 가이드

현재 메시지:
- `kubectl: command not found`
- `eksctl: command not found`

즉, **WSL(우분투) 환경에 `kubectl` / `eksctl`이 설치되어 있지 않아서** 발생한 상황입니다.  
아래 순서대로 진행하면 **설치 → 버전 확인 → AWS 자격증명/리전 확인 → EKS kubeconfig 연결**까지 한 번에 됩니다.

---

## 1) 필수 패키지 업데이트

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl unzip gnupg
```

---

## 2) `kubectl` 설치 (권장: 공식 바이너리)

> `snap`으로도 설치 가능하지만, 실무에서는 공식 바이너리가 깔끔합니다.

```bash
# kubectl 최신 stable 다운로드
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# checksum 검증(권장)
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check

# 설치
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 확인
kubectl version --client --output=yaml
```

---

## 3) `eksctl` 설치 (공식 릴리즈 바이너리)

```bash
# 다운로드 & 설치
curl --silent --location "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz" \
  | tar xz -C /tmp

sudo install -o root -g root -m 0755 /tmp/eksctl /usr/local/bin/eksctl

# 확인
eksctl version
```

---

## 4) AWS CLI 설치/확인 (이미 있다면 스킵)

```bash
aws --version || true
```

만약 없다면:

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
unzip -q /tmp/awscliv2.zip -d /tmp
sudo /tmp/aws/install
aws --version
```

---

## 5) AWS 자격증명 + 리전 확인

```bash
aws sts get-caller-identity
aws configure list
aws configure get region
```

리전이 비어있으면(예: 서울 `ap-northeast-2`):

```bash
aws configure set region ap-northeast-2
```

---

## 6) EKS 클러스터 목록 확인

```bash
eksctl get cluster --region ap-northeast-2
# 또는
aws eks list-clusters --region ap-northeast-2
```

---

## 7) kubeconfig 연결 (EKS 접속 준비)

클러스터 이름을 `MYCLUSTER`로 바꿔서 실행:

```bash
aws eks update-kubeconfig --region ap-northeast-2 --name eksdemo2
kubectl get nodes
```

---

# 자주 막히는 포인트 3개 (빠른 체크)

## A) PATH 문제

```bash
which kubectl && which eksctl && echo $PATH
```

- 둘 다 `/usr/local/bin/...` 로 나오면 정상입니다.

## B) 권한(AccessDenied) 문제

`aws sts get-caller-identity`는 되는데 EKS 조회가 안 되면, IAM 정책에 아래 액션들이 없을 수 있습니다:

- `eks:DescribeCluster`
- `eks:ListClusters`

## C) “kubeconfig는 됐는데 kubectl이 접근 못함”

```bash
kubectl config current-context
kubectl cluster-info
```

---

# 원인 파악용 출력(민감정보 없음)

아래 6줄 출력만 공유하면, 어디서 막혔는지 빠르게 좁힐 수 있습니다.

```bash
uname -a
lsb_release -a 2>/dev/null || cat /etc/os-release
echo $PATH
which aws && aws --version
which kubectl && kubectl version --client --short
which eksctl && eksctl version
```
---

### 구성도 EKS Guide URL

https://docs.aws.amazon.com/eks/

![image](./image2.png)

https://aws.amazon.com/blogs/containers/saas-deployment-architectures-with-amazon-eks/

https://aws.amazon.com/blogs/architecture/field-notes-managing-an-amazon-eks-cluster-using-aws-cdk-and-cloud-resource-property-manager/


### 전체 플로우
```
flowchart TD
  %% =========================
  %% EKS 설치 Flow (eksctl 기준)
  %% =========================

  A["사전 준비"] --> A1["로컬 도구 설치/확인<br/>- awscli v2<br/>- eksctl<br/>- kubectl<br/>- (선택) helm"]
  A1 --> A2["AWS 인증/권한 확인<br/>- aws configure 또는 SSO/AssumeRole<br/>- sts get-caller-identity"]
  A2 --> A3["리전/쿼터/이름 규칙 결정<br/>- ap-northeast-2 등<br/>- 클러스터명/노드그룹명"]

  A3 --> B{"VPC를 새로 만들까?"}
  B -- 예(기본) --> B1["eksctl이 VPC 자동 생성<br/>Public/Private Subnet + NAT 포함"]
  B -- 아니오(기존) --> B2["기존 VPC 사용 준비<br/>- subnet IDs 준비<br/>- 태그 확인: kubernetes.io/cluster/CLUSTER, role/elb, role/internal-elb"]
  B1 --> C
  B2 --> C

  C{"클러스터 정의 방식?"}
  C -- CLI로 빠르게 --> C1["eksctl create cluster<br/>--name CLUSTER<br/>--region REGION<br/>--version X.Y<br/>--managed"]
  C -- YAML로 표준화 --> C2["cluster.yaml 작성<br/>- metadata(name/region/version)<br/>- vpc 설정(자동/기존)<br/>- managedNodeGroups 등"]
  C1 --> D
  C2 --> D1["eksctl create cluster -f cluster.yaml"]
  D1 --> D

  D["Control Plane 생성 완료"] --> E["kubeconfig 설정<br/>aws eks update-kubeconfig<br/>또는 eksctl utils write-kubeconfig"]
  E --> F["기본 점검<br/>kubectl get nodes<br/>kubectl get pods -A"]

  F --> G{"IRSA(서비스어카운트 IAM) 쓸까?"}
  G -- 예(권장) --> G1["OIDC Provider 연결<br/>eksctl utils associate-iam-oidc-provider<br/>--cluster CLUSTER --region REGION --approve"]
  G -- 아니오 --> H

  G1 --> H["노드/컴퓨팅 구성"]
  H --> H1{"노드 방식?"}
  H1 -- Managed NodeGroup(권장) --> H2["노드그룹 생성/추가<br/>eksctl create nodegroup<br/>--cluster CLUSTER --name NG<br/>--node-type t3.large<br/>--nodes 2 --nodes-min 2 --nodes-max 5<br/>--managed"]
  H1 -- Fargate(선택) --> H3["Fargate Profile 생성<br/>eksctl create fargateprofile<br/>--cluster CLUSTER --name FP<br/>--namespace NS"]
  H2 --> I
  H3 --> I

  I["필수 애드온 확인/정리"] --> I1["AWS-managed add-on 권장 흐름<br/>- vpc-cni<br/>- coredns<br/>- kube-proxy"]
  I1 --> I2["eksctl create addon / update addon (선택)<br/>또는 콘솔에서 Add-ons 관리"]

  I2 --> J{"스토리지 필요?"}
  J -- EBS 필요 --> J1["EBS CSI Driver 설치(권장: IRSA 사용)<br/>1) (IRSA) IAM Role/Policy 준비<br/>2) eksctl create addon aws-ebs-csi-driver<br/>3) StorageClass/PVC 테스트"]
  J -- 불필요 --> K
  J1 --> K

  K{"Ingress/LB 필요?"}
  K -- ALB(권장) --> K1["AWS Load Balancer Controller<br/>- (필수) IRSA Role/Policy<br/>- helm repo add / helm install<br/>- IngressClass/annotations 구성"]
  K -- NGINX 등 --> K2["NGINX Ingress Controller(선택)<br/>- helm install ingress-nginx<br/>- Service 타입(LB) 확인"]
  K1 --> L
  K2 --> L

  L["인증/권한 운영 설정(권장)"] --> L1["aws-auth(클러스터 접근자) 관리<br/>- IAM Role/User 매핑<br/>- 팀별 RBAC(Role/RoleBinding)"]
  L1 --> M["검증 단계"]
  M --> M1["샘플 앱 배포<br/>Deployment + Service + Ingress"]
  M1 --> M2["네트워크/DNS 확인<br/>- nslookup/curl 테스트<br/>- CoreDNS 정상"]
  M2 --> M3["오토스케일(선택)<br/>- metrics-server 설치/확인<br/>- HPA 테스트"]
  M3 --> N["운영 준비<br/>- 업그레이드 전략(버전/노드 롤링)<br/>- 로깅/모니터링(CloudWatch 등)<br/>- CI/CD 연동"]
  ```

  ![image](./image.png)

  
---

```
# 1) 클러스터(컨트롤 플레인) 생성 - 저장소 가이드 기준
eksctl create cluster \
  --name eksdemo2 \
  --region ap-northeast-2 \
  --zones ap-northeast-2a,ap-northeast-2b \
  --without-nodegroup
```
---
```
# 2) OIDC 연결
eksctl utils associate-iam-oidc-provider \
  --region ap-northeast-2 \
  --cluster eksdemo2 \
  --approve
```
---
```
# 3) 노드그룹 생성(관리형)

```
---
```
# 4) 확인
eksctl get cluster --region ap-northeast-2
eksctl get nodegroup --cluster eksdemo2 --region ap-northeast-2
kubectl get nodes -o wide
```
---
eksctl create nodegroup \
  --cluster eksdemo2 \
  --region ap-northeast-2 \
  --name eksdemo2-ng-public1 \
  --node-type t3.medium \
  --nodes 1 \
  --nodes-min 1 \
  --nodes-max 2 \
  --node-volume-size 20 \
  --managed