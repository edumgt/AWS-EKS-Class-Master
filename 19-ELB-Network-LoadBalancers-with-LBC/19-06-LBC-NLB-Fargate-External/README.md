---
title: AWS Load Balancer Controller - NLB & Fargate
description: Fargate 파드에서 AWS Network Load Balancer를 사용하는 방법 학습
---

## 단계-01: 소개
- 고급 AWS Fargate 프로파일 생성
- App3를 Fargate 파드에 스케줄
- NLB 애노테이션 `aws-load-balancer-nlb-target-type`를 `instance` 모드에서 `ip`로 변경

## 단계-02: Fargate 프로파일 검토
- **파일 이름:** `fargate-profile/01-fargate-profiles.yml`
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: eksdemo1  # Name of the EKS Cluster
  region: ap-northeast-2
fargateProfiles:
  - name: fp-app3
    selectors:
      # All workloads in the "ns-app3" Kubernetes namespace will be
      # scheduled onto Fargate:      
      - namespace: ns-app3
```

## 단계-03: Fargate 프로파일 생성
```t
# 디렉터리 이동
cd 19-06-LBC-NLB-Fargate-External

# Fargate 프로파일 생성
eksctl create fargateprofile -f fargate-profile/01-fargate-profiles.yml
```

## 단계-04: aws-load-balancer-nlb-target-type 애노테이션을 IP로 변경
- **파일 이름:** `kube-manifests/02-LBC-NLB-LoadBalancer-Service.yml`
```yaml
service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip # For Fargate Workloads we should use target-type as ip
```

## 단계-05: 네임스페이스용 K8s Deployment 메타데이터 검토
- **파일 이름:** `kube-manifests/01-Nginx-App3-Deployment.yml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app3-nginx-deployment
  labels:
    app: app3-nginx 
  namespace: ns-app3    # Fargate 프로파일 01-fargate-profiles.yml에 지정한 네임스페이스로 업데이트
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app3-nginx
  template:
    metadata:
      labels:
        app: app3-nginx
    spec:
      containers:
        - name: app2-nginx
          image: stacksimplify/kubenginx:1.0.0
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "128Mi"
              cpu: "500m"
            limits:
              memory: "500Mi"
              cpu: "1000m"           
```

## 단계-06: kube-manifests 전체 배포
```t
# kube-manifests 배포
kubectl apply -f kube-manifests/

# 파드 확인
kubectl get pods -o wide
관찰 사항:
1. Fargate 모드로 인해 파드가 Pending에서 Running으로 전환되기까지 몇 분이 걸릴 수 있습니다.

# 워커 노드 확인
kubectl get nodes -o wide
관찰 사항:
1. Fargate 워커 노드가 생성될 때까지 대기합니다.

# 서비스 확인
kubectl get svc
관찰 사항:
1. 네트워크 LB DNS 이름 확인

# AWS Load Balancer Controller 파드 로그 확인
kubectl -n kube-system get pods
kubectl -n kube-system logs -f <aws-load-balancer-controller-POD-NAME>

# AWS 관리 콘솔에서 확인
Services -> EC2 -> Load Balancing -> Load Balancers로 이동
1. Description 탭에서 "kubectl get svc" External IP와 일치하는 DNS Name 확인
2. Listeners 탭 확인

Services -> EC2 -> Load Balancing -> Target Groups로 이동
1. 등록된 대상 확인
2. Health Check 경로 확인

# nslookup 테스트 수행
nslookup nlbfargate901.stacksimplify.com

# 애플리케이션 접속
# HTTP URL 테스트
http://nlbfargate901.stacksimplify.com

# HTTPS URL 테스트
https://nlbfargate901.stacksimplify.com
```

## 단계-06: 정리
```t
# kube-manifests 삭제 또는 언배포
kubectl delete -f kube-manifests/

# NLB 삭제 여부 확인
AWS 관리 콘솔에서,
Services -> EC2 -> Load Balancing -> Load Balancers로 이동
```

## 참고 자료
- [Network Load Balancer](https://docs.aws.amazon.com/eks/latest/userguide/network-load-balancing.html)
- [NLB Service](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/service/nlb/)
- [NLB Service Annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/service/annotations/)











## 단계-09: Fargate 프로파일 삭제
```t
# Fargate 프로파일 목록
eksctl get fargateprofile --cluster eksdemo1 

# Fargate 프로파일 삭제
eksctl delete fargateprofile --cluster eksdemo1 --name <Fargate-Profile-NAME> --wait

eksctl delete fargateprofile --cluster eksdemo1 --name  fp-app3 --wait
```
