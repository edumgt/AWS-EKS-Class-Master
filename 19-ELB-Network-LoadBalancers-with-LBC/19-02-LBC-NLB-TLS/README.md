---
title: AWS Load Balancer Controller - NLB TLS
description: AWS Load Balancer Controller로 AWS Network Load Balancer TLS를 사용하는 방법 학습
---

## 단계-01: 소개
- Network Load Balancer용 TLS 애노테이션 4가지를 이해합니다.
- aws-load-balancer-ssl-cert
- aws-load-balancer-ssl-ports
- aws-load-balancer-ssl-negotiation-policy
- aws-load-balancer-ssl-negotiation-policy

## 단계-02: TLS 애노테이션 검토
- **파일 이름:** `kube-manifests\\02-LBC-NLB-LoadBalancer-Service.yml`
- **보안 정책:** https://docs.aws.amazon.com/elasticloadbalancing/latest/network/create-tls-listener.html#describe-ssl-policies
```yaml
    # TLS
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:ap-northeast-2:180789647333:certificate/d86de939-8ffd-410f-adce-0ce1f5be6e0d
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: 443, # Specify this annotation if you need both TLS and non-TLS listeners on the same load balancer
    service.beta.kubernetes.io/aws-load-balancer-ssl-negotiation-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp 
```


## 단계-03: kube-manifests 전체 배포
```t
# Deploy kube-manifests
kubectl apply -f kube-manifests/

# 파드 확인
kubectl get pods

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
관찰 사항: 포트 80과 443의 두 리스너가 보여야 합니다.

Services -> EC2 -> Load Balancing -> Target Groups로 이동
1. 등록된 대상 확인
2. Health Check 경로 확인
관찰 사항: 타깃 그룹 2개가 보여야 하며, 리스너 1개당 타깃 그룹 1개입니다.

# 애플리케이션 접속
# HTTP URL 테스트
http://<NLB-DNS-NAME>
http://lbc-network-lb-tls-demo-a956479ba85953f8.elb.ap-northeast-2.amazonaws.com

# HTTPS URL 테스트
https://<NLB-DNS-NAME>
https://lbc-network-lb-tls-demo-a956479ba85953f8.elb.ap-northeast-2.amazonaws.com
```

## 단계-04: 정리
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
