---
title: AWS Load Balancer Controller 설치(AWS EKS)
description: AWS EKS에서 Ingress 구현을 위한 AWS Load Balancer Controller 설치 학습
---

# AWS Load Balancer Controller 설치

## 단계-00: 소개
1. IAM 정책을 생성하고 Policy ARN을 기록합니다.
2. IAM Role과 Kubernetes ServiceAccount를 생성하고 바인딩합니다.
3. Helm 3로 AWS Load Balancer Controller를 설치합니다.
4. IngressClass 개념을 이해하고 기본 IngressClass를 생성합니다.

## 단계-01: 사전 준비

### 사전 준비-1: `eksctl` 및 `kubectl` 준비
- 최신 `eksctl` 버전을 사용하는 것을 권장합니다.
- `kubectl` 버전은 EKS 컨트롤 플레인과 마이너 버전 차이가 1 이하가 되도록 맞춥니다.

```bash
# eksctl 버전 확인
eksctl version

# 최신 eksctl 설치 또는 업그레이드
# https://docs.aws.amazon.com/eks/latest/userguide/eksctl.html

# EKS 클러스터 버전 확인
kubectl version --short
kubectl version

# kubectl CLI 설치
# https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html
```

### 사전 준비-2: EKS 클러스터 및 워커 노드 생성
- 아직 클러스터가 없다면 아래 예시를 참고해 생성합니다.
- 예시 값은 `eksdemo1`, `us-east-1` 기준입니다.

```bash
# 클러스터 생성
eksctl create cluster --name=eksdemo1 \
                      --region=us-east-1 \
                      --zones=us-east-1a,us-east-1b \
                      --version="1.21" \
                      --without-nodegroup

# 클러스터 목록 확인
eksctl get cluster

# OIDC Provider 연결 템플릿
eksctl utils associate-iam-oidc-provider \
    --region region-code \
    --cluster <cluster-name> \
    --approve

# 예시
eksctl utils associate-iam-oidc-provider \
    --region us-east-1 \
    --cluster eksdemo1 \
    --approve

# 프라이빗 서브넷용 EKS NodeGroup 생성 예시
eksctl create nodegroup --cluster=eksdemo1 \
                        --region=us-east-1 \
                        --name=eksdemo1-ng-private1 \
                        --node-type=t3.medium \
                        --nodes-min=2 \
                        --nodes-max=4 \
                        --node-volume-size=20 \
                        --ssh-access \
                        --ssh-public-key=kube-demo \
                        --managed \
                        --asg-access \
                        --external-dns-access \
                        --full-ecr-access \
                        --appmesh-access \
                        --alb-ingress-access \
                        --node-private-networking
```

### 사전 준비-3: 클러스터/노드 그룹 확인 및 `kubectl` 설정

```bash
# EKS 클러스터 확인
eksctl get cluster

# EKS 노드 그룹 확인
eksctl get nodegroup --cluster=eksdemo1

# IAM ServiceAccount 존재 여부 확인
eksctl get iamserviceaccount --cluster=eksdemo1

# kubeconfig 설정
aws eks --region <region-code> update-kubeconfig --name <cluster-name>
aws eks --region us-east-1 update-kubeconfig --name eksdemo1

# 노드 확인
kubectl get nodes
```

관찰 포인트:
- 처음에는 `eksctl get iamserviceaccount --cluster=eksdemo1` 결과가 비어 있을 수 있습니다.
- AWS 콘솔에서는 EKS 클러스터와 EC2 노드, 서브넷 위치를 함께 확인해두면 이후 실습이 편합니다.

## 단계-02: IAM 정책 생성
- AWS Load Balancer Controller가 AWS API를 호출할 수 있도록 IAM 정책을 생성합니다.
- 최신 정책 파일은 공식 GitHub 저장소에서 가져옵니다.
- 참고: [AWS Load Balancer Controller GitHub](https://github.com/kubernetes-sigs/aws-load-balancer-controller)

```bash
# 디렉터리 이동
cd 08-NEW-ELB-Application-LoadBalancers/
cd 08-01-Load-Balancer-Controller-Install

# 기존 파일 삭제(있는 경우)
rm -f iam_policy_latest.json

# 최신 정책 다운로드
curl -o iam_policy_latest.json \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

# 다운로드 확인
ls -lrta

# 특정 버전 예시
curl -o iam_policy_v2.3.1.json \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.3.1/docs/install/iam_policy.json

# IAM 정책 생성
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy_latest.json
```

출력 예시:

```json
{
  "Policy": {
    "PolicyName": "AWSLoadBalancerControllerIAMPolicy",
    "Arn": "arn:aws:iam::180789647333:policy/AWSLoadBalancerControllerIAMPolicy"
  }
}
```

중요:
- AWS 콘솔에서 일부 ELB 관련 경고가 보일 수 있습니다.
- 이는 ELB v2 전용 액션과 관련된 경고일 수 있으며, 일반적으로 무시해도 됩니다.

### Policy ARN 기록
- 다음 단계에서 IAM Role 생성 시 사용하므로 기록해둡니다.

```text
Policy ARN: arn:aws:iam::086015456585:policy/AWSLoadBalancerControllerIAMPolicy
```

## 보충: `kube-system`에 `*-controller` ServiceAccount가 보이는 이유

```bash
kubectl get sa -n kube-system
```

핵심 정리:
- `ServiceAccount`는 사람이 쓰는 계정이 아니라 클러스터 내부 워크로드가 쓰는 계정입니다.
- `kube-system`에는 컨트롤러와 애드온이 많아서 `*-controller` 이름의 ServiceAccount가 자주 보입니다.
- 최근 쿠버네티스에서는 SA마다 장기 Secret 토큰이 자동 생성되지 않을 수 있어서 `SECRETS 0`이 자연스러운 경우가 많습니다.

확인 명령:

```bash
# ServiceAccount 상세 확인
kubectl -n kube-system describe sa <sa-name>

# 해당 SA를 사용하는 파드 찾기
kubectl -n kube-system get pod \
  -o custom-columns=NAME:.metadata.name,SA:.spec.serviceAccountName | grep <sa-name>

# 권한 확인
kubectl auth can-i --as=system:serviceaccount:kube-system:<sa-name> get pods -n kube-system
kubectl auth can-i --as=system:serviceaccount:kube-system:<sa-name> '*' '*' -n kube-system
```

## 단계-03: IAM Role 생성 및 Kubernetes ServiceAccount 바인딩
- `eksctl`로 관리되는 클러스터 기준 예시입니다.
- 이 단계에서 AWS IAM Role과 Kubernetes ServiceAccount를 함께 생성하고 연결합니다.

### 단계-03-01: `eksctl`로 IAM Role 생성

먼저 확인:

```bash
kubectl get sa -n kube-system
kubectl get sa aws-load-balancer-controller -n kube-system
```

관찰 포인트:
- `aws-load-balancer-controller` ServiceAccount가 아직 없을 수 있습니다.

OIDC Provider 연결:

```bash
eksctl utils associate-iam-oidc-provider \
  --region ap-northeast-2 \
  --cluster eksdemo1 \
  --approve
```

IAM Role + ServiceAccount 생성:

```bash
eksctl create iamserviceaccount \
  --cluster eksdemo1 \
  --namespace kube-system \
  --name aws-load-balancer-controller \
  --attach-policy-arn arn:aws:iam::086015456585:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve
```

출력 예시:

```text
created serviceaccount "kube-system/aws-load-balancer-controller"
```

### 단계-03-02: `eksctl`로 IAM ServiceAccount 확인

```bash
eksctl get iamserviceaccount --cluster eksdemo1
```

예시:

```text
NAMESPACE       NAME                            ROLE ARN
kube-system     aws-load-balancer-controller    arn:aws:iam::086015456585:role/eksctl-eksdemo1-addon-iamserviceaccount-kube--Role1-xxxx
```

### 단계-03-03: CloudFormation 및 IAM Role 확인
- AWS 콘솔에서 `CloudFormation`으로 이동합니다.
- 스택 이름 예시: `eksctl-eksdemo1-addon-iamserviceaccount-kube-system-aws-load-balancer-controller`
- `Resources` 탭에서 생성된 IAM Role의 `Physical ID`를 확인합니다.

### 단계-03-04: `kubectl`로 ServiceAccount 확인

```bash
kubectl get sa -n kube-system
kubectl get sa aws-load-balancer-controller -n kube-system
kubectl describe sa aws-load-balancer-controller -n kube-system
```

관찰 포인트:
- `Annotations`에 Role ARN이 있어야 합니다.
- 이는 AWS IAM Role과 Kubernetes ServiceAccount가 바인딩되었다는 의미입니다.

예시:

```text
Annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::180789647333:role/eksctl-eksdemo1-addon-iamserviceaccount-kube-Role1-xxxx
```

## 단계-04: Helm v3로 AWS Load Balancer Controller 설치

### 단계-04-01: Helm 설치
- 미설치 시 [Helm 설치 문서](https://helm.sh/docs/intro/install/)를 참고합니다.
- AWS EKS용 참고 문서: [Helm on Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/helm.html)

```bash
# macOS 예시
brew install helm

# 버전 확인
helm version
```

WSL 예시:

```bash
sudo snap install helm --classic
```

### 단계-04-02: AWS Load Balancer Controller 설치

중요:
- IMDS 접근이 제한된 EC2 노드나 Fargate에 배포하는 경우 아래 값을 추가할 수 있습니다.

```text
--set region=region-code
--set vpcId=vpc-xxxxxxxx
```

- 예전에는 리전별 ECR 이미지를 직접 지정하는 방식이 있었지만, 현재는 Public ECR 이미지를 사용하는 구성이 더 간단합니다.

```bash
# Helm repo 추가
helm repo add eks https://aws.github.io/eks-charts

# repo 업데이트
helm repo update

# 컨트롤러 설치
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=eksdemo1 \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set region=ap-northeast-2 \
  --set vpcId=vpc-052b0119f527ad248 \
  --set image.repository=public.ecr.aws/eks/aws-load-balancer-controller
```

결과 예시:

```text
NAME: aws-load-balancer-controller
NAMESPACE: kube-system
STATUS: deployed
```

### 단계-04-03: 설치 및 Webhook Service 확인

```bash
# Deployment 확인
kubectl -n kube-system get deployment
kubectl -n kube-system get deployment aws-load-balancer-controller
kubectl -n kube-system describe deployment aws-load-balancer-controller

# Webhook Service 확인
kubectl -n kube-system get svc
kubectl -n kube-system get svc aws-load-balancer-webhook-service
kubectl -n kube-system describe svc aws-load-balancer-webhook-service

# 라벨과 셀렉터 확인
kubectl -n kube-system get svc aws-load-balancer-webhook-service -o yaml
kubectl -n kube-system get deployment aws-load-balancer-controller -o yaml
```

관찰 포인트:
1. `aws-load-balancer-webhook-service`의 `spec.selector` 확인
2. `aws-load-balancer-controller` Deployment의 `spec.selector.matchLabels`와 비교
3. 두 값이 일치해야 서비스가 파드로 정상 연결됩니다.

### 단계-04-04: 컨트롤러 로그 확인

```bash
kubectl get pods -n kube-system

kubectl -n kube-system logs -f <POD-NAME>
kubectl -n kube-system logs -f aws-load-balancer-controller-68596697df-kqp5s

kubectl -n kube-system logs -f <POD-NAME>
kubectl -n kube-system logs -f aws-load-balancer-controller-86b598cbd6-vqqsk
```

### 단계-04-05: ServiceAccount 내부 확인

JWT 토큰을 직접 확인해볼 수 있습니다.

```bash
kubectl -n kube-system create token aws-load-balancer-controller --duration=10m
```

참고:
- 디코딩 확인: <https://jwt.io/>

Deployment와 Pod의 ServiceAccount 연결 확인:

```bash
# Deployment 확인
kubectl -n kube-system get deploy aws-load-balancer-controller -o yaml

# Pod 확인
kubectl -n kube-system get pods
kubectl -n kube-system get pod <AWS-Load-Balancer-Controller-POD-NAME> -o yaml
kubectl -n kube-system get pod aws-load-balancer-controller-696b745696-n56bg -o yaml
```

관찰 포인트:
1. `spec.template.spec.serviceAccount` 또는 `serviceAccountName`
2. 값이 `aws-load-balancer-controller`인지 확인
3. `aws-iam-token` 볼륨과 `AWS_WEB_IDENTITY_TOKEN_FILE` 환경 변수 확인

예시:

```yaml
volumes:
  - name: aws-iam-token
    projected:
      defaultMode: 420
      sources:
        - serviceAccountToken:
            audience: sts.amazonaws.com
            expirationSeconds: 86400
            path: token
```

```yaml
volumeMounts:
  - mountPath: /var/run/secrets/eks.amazonaws.com/serviceaccount
    name: aws-iam-token
    readOnly: true
```

```yaml
- name: AWS_WEB_IDENTITY_TOKEN_FILE
  value: /var/run/secrets/eks.amazonaws.com/serviceaccount/token
```

### 단계-04-06: TLS 인증서 확인

```bash
# Secret 확인
kubectl -n kube-system get secret aws-load-balancer-tls -o yaml

# Pod 확인
kubectl -n kube-system get pods
kubectl -n kube-system get pod <AWS-Load-Balancer-Controller-POD-NAME> -o yaml
kubectl -n kube-system get pod aws-load-balancer-controller-65b4f64d6c-h2vh4 -o yaml
```

참고 사이트:
- <https://www.base64decode.org/>
- <https://www.sslchecker.com/certdecoder>

관찰 포인트:
- `Common Name`: `aws-load-balancer-controller`
- `SAN` 예시:
  - `aws-load-balancer-webhook-service.kube-system`
  - `aws-load-balancer-webhook-service.kube-system.svc`

마운트 확인 예시:

```yaml
volumeMounts:
  - mountPath: /tmp/k8s-webhook-server/serving-certs
    name: cert
    readOnly: true
```

```yaml
volumes:
  - name: cert
    secret:
      defaultMode: 420
      secretName: aws-load-balancer-tls
```

### 단계-04-07: 제거 명령(참고용)
- 아래 명령은 참고용입니다. 문서 학습 중에는 실행하지 않아도 됩니다.

```bash
helm uninstall aws-load-balancer-controller -n kube-system
```

## 단계-05: IngressClass 개념
- IngressClass가 무엇인지 이해합니다.
- 예전 애노테이션 방식인 `kubernetes.io/ingress.class: "alb"`를 어떻게 대체하는지 이해합니다.
- 참고:
  - [Ingress Class 문서](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/ingress_class/)
  - [Ingress Controller 개요](https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/)

## 단계-06: IngressClass 매니페스트 검토
- 파일 위치: `08-01-Load-Balancer-Controller-Install/kube-manifests/01-ingressclass-resource.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: IngressClass
metadata:
  name: my-aws-ingress-class
  annotations:
    ingressclass.kubernetes.io/is-default-class: "true"
spec:
  controller: ingress.k8s.aws/alb
```

정리:
1. 특정 IngressClass를 클러스터 기본값으로 지정할 수 있습니다.
2. `ingressclass.kubernetes.io/is-default-class: "true"`를 지정하면 `ingressClassName`이 없는 새 Ingress가 기본 IngressClass를 사용합니다.
3. 참고: <https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.3/guide/ingress/ingress_class/>

## 단계-07: IngressClass 리소스 생성

```bash
cd 08-01-Load-Balancer-Controller-Install

# IngressClass 생성
kubectl apply -f kube-manifests

# 확인
kubectl get ingressclass
kubectl describe ingressclass my-aws-ingress-class
```

## 참고: EKS에서 ALB와 Traefik 선택
- EKS에서는 외부 HTTP/HTTPS 진입점으로 AWS Load Balancer Controller + ALB 구성이 가장 흔합니다.
- AWS 네이티브 기능(ACM, WAF, 보안 그룹, 타겟 그룹, 헬스 체크)과 잘 통합됩니다.
- Traefik도 사용할 수 있으며, 다음과 같이 선택하는 경우가 많습니다.

정리:
- AWS 기능을 적극 활용하는 표준 외부 진입점: `ALB Ingress`
- TCP/UDP 중심: `NLB`
- 클러스터 내부 게이트웨이 기능과 미들웨어가 중요: `ALB/NLB + Traefik`

## 참고 자료
- [AWS Load Balancer Controller 설치 문서](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Amazon EKS add-on 이미지 주소](https://docs.aws.amazon.com/eks/latest/userguide/add-ons-images.html)
