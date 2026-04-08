---
title: AWS Load Balancer Controller - External DNS 설치
description: AWS Load Balancer Controller - External DNS 설치 학습
---

## 단계-01: 소개
- **External DNS:** Kubernetes에서 Route53 RecordSet을 업데이트하는 데 사용합니다.
- external-dns 파드가 AWS Route53 Hosted Zone의 레코드를 추가/삭제할 수 있도록 IAM Policy, K8s Service Account, IAM Role을 생성하고 연결합니다.
- External-DNS 기본 매니페스트를 필요에 맞게 수정합니다.
- 배포 후 로그를 확인합니다.

## 단계-02: IAM 정책 생성
- 이 IAM 정책은 external-dns 파드가 AWS Route53 서비스의 DNS 레코드(Hosted Zone의 Record Set)를 추가/삭제할 수 있게 합니다.
- Services -> IAM -> Policies -> Create Policy로 이동
  - **JSON** 탭 클릭 후 아래 JSON 붙여넣기
  - **Visual editor** 탭에서 검증
  - **Review Policy** 클릭
  - **Name:** AllowExternalDNSUpdates
  - **Description:** Allow access to Route53 Resources for ExternalDNS
  - **Create Policy** 클릭

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": [
        "arn:aws:route53:::hostedzone/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```
- 다음 단계에서 사용할 Policy ARN을 기록합니다.
```t
# Policy ARN
arn:aws:iam::180789647333:policy/AllowExternalDNSUpdates
```  


## 단계-03: IAM Role, K8s Service Account 생성 및 IAM 정책 연결
- 이 단계에서 `external-dns`라는 K8s Service Account를 생성하고 AWS IAM Role을 만들어 Service Account에 role ARN을 애노테이션으로 연결합니다.
- 또한 새로 만든 IAM Role에 `AllowExternalDNSUpdates` IAM 정책을 연결합니다.
### 단계-03-01: IAM Role, K8s Service Account 생성 및 IAM 정책 연결
```t
# 템플릿
eksctl create iamserviceaccount \
    --name service_account_name \
    --namespace service_account_namespace \
    --cluster cluster_name \
    --attach-policy-arn IAM_policy_ARN \
    --approve \
    --override-existing-serviceaccounts

# name, namespace, cluster, IAM Policy ARN을 실제 값으로 교체
eksctl create iamserviceaccount \
    --name external-dns \
    --namespace default \
    --cluster eksdemo1 \
    --attach-policy-arn arn:aws:iam::180789647333:policy/AllowExternalDNSUpdates \
    --approve \
    --override-existing-serviceaccounts
```
### 단계-03-02: Service Account 확인
- external-dns Service Account를 확인하고, IAM Role 관련 애노테이션을 검증합니다.
```t
# Service Account 목록
kubectl get sa external-dns

# Service Account 상세 확인
kubectl describe sa external-dns
관찰 사항:
1. 애노테이션을 확인하여 Service Account에 IAM Role이 있는지 확인합니다.
```
### 단계-03-03: CloudFormation 스택 확인
- Services -> CloudFormation으로 이동
- 최신 CFN 스택 생성 여부 확인
- **Resources** 탭 클릭
- **Physical ID** 필드의 링크를 클릭해 **IAM Role**로 이동

### 단계-03-04: IAM Role 및 IAM 정책 확인
- 위 CFN 단계에서 external-dns용 IAM Role로 이동합니다.
- **Permissions** 탭에서 **AllowExternalDNSUpdates** 정책이 있는지 확인합니다.
- Role ARN을 기록해 External-DNS K8s 매니페스트에 반영합니다.
```t
# Role ARN 기록
arn:aws:iam::180789647333:role/eksctl-eksdemo1-addon-iamserviceaccount-defa-Role1-JTO29BVZMA2N
```

### 단계-03-05: eksctl로 IAM Service Accounts 확인
- 여기서도 External DNS Role ARN을 확인할 수 있습니다.
```t
# eksctl로 IAM Service Accounts 목록
eksctl get iamserviceaccount --cluster eksdemo1

# 출력 예시
Kalyans-Mac-mini:08-06-ALB-Ingress-ExternalDNS kalyanreddy$ eksctl get iamserviceaccount --cluster eksdemo1
2022-02-11 09:34:39 [ℹ]  eksctl version 0.71.0
2022-02-11 09:34:39 [ℹ]  using region ap-northeast-2
NAMESPACE	NAME				ROLE ARN
default		external-dns			arn:aws:iam::180789647333:role/eksctl-eksdemo1-addon-iamserviceaccount-defa-Role1-JTO29BVZMA2N
kube-system	aws-load-balancer-controller	arn:aws:iam::180789647333:role/eksctl-eksdemo1-addon-iamserviceaccount-kube-Role1-EFQB4C26EALH
Kalyans-Mac-mini:08-06-ALB-Ingress-ExternalDNS kalyanreddy$ 
```


## 단계-04: External DNS Kubernetes 매니페스트 업데이트
- **원본 템플릿:** https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
- **파일 위치:** kube-manifests/01-Deploy-ExternalDNS.yml
### 변경-1: 9번째 줄 IAM Role 업데이트
  - 단계-03에서 기록한 role-arn을 9번째 줄에 반영합니다.
```yaml
    eks.amazonaws.com/role-arn: arn:aws:iam::180789647333:role/eksctl-eksdemo1-addon-iamserviceaccount-defa-Role1-JTO29BVZMA2N
```
### 변경-2: 55, 56번째 줄 주석 처리
- eksctl로 IAM Role을 만들고 `AllowExternalDNSUpdates` 정책을 연결했습니다.
- KIAM 또는 Kube2IAM을 사용하지 않으므로 해당 두 줄은 필요 없어 주석 처리합니다.
```yaml
      #annotations:  
        #iam.amazonaws.com/role: arn:aws:iam::ACCOUNT-ID:role/IAM-SERVICE-ROLE-NAME    
```
### 변경-3: 65, 67번째 줄 주석 처리
```yaml
        # - --domain-filter=external-dns-test.my-org.com # will make ExternalDNS see only the hosted zones matching provided domain, omit to process all available hosted zones
       # - --policy=upsert-only # would prevent ExternalDNS from deleting any records, omit to enable full synchronization
```

### 변경-4: 61번째 줄 최신 Docker 이미지 이름 확인
- [최신 external-dns 이미지 이름 확인](https://github.com/kubernetes-sigs/external-dns/releases/tag/v0.10.2)
```yaml
    spec:
      serviceAccountName: external-dns
      containers:
      - name: external-dns
        image: k8s.gcr.io/external-dns/external-dns:v0.10.2
```

## 단계-05: ExternalDNS 배포
- 매니페스트 배포
```t
# 디렉터리 이동
cd 08-06-Deploy-ExternalDNS-on-EKS

# External DNS 배포
kubectl apply -f kube-manifests/

# default 네임스페이스의 모든 리소스 목록
kubectl get all

# 파드 목록(external-dns 파드는 running 상태여야 함)
kubectl get pods

# 로그로 Deployment 확인
kubectl logs -f $(kubectl get po | egrep -o 'external-dns[A-Za-z0-9-]+')
```

## 참고 자료
- https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/alb-ingress.md
- https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md

