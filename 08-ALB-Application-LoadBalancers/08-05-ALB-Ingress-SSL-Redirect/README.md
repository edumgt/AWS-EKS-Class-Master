---
title: AWS Load Balancer - Ingress SSL HTTP에서 HTTPS 리디렉션
description: AWS Load Balancer - Ingress SSL HTTP에서 HTTPS 리디렉션 학습
---

## 단계-01: SSL 리디렉션 관련 애노테이션 추가
- **파일 이름:** 04-ALB-Ingress-SSL-Redirect.yml
- HTTP에서 HTTPS로 리디렉션
```yaml
    # SSL Redirect Setting
    alb.ingress.kubernetes.io/ssl-redirect: '443'   
```

## 단계-02: 모든 매니페스트 배포 및 테스트

### 배포 및 확인
```t
# kube-manifests 배포
kubectl apply -f kube-manifests/

# Ingress 리소스 확인
kubectl get ingress

# 앱 확인
kubectl get deploy
kubectl get pods

# NodePort 서비스 확인
kubectl get svc
```
### Load Balancer 및 Target Groups 확인
- Load Balancer - Listeners(80과 443 확인)
- Load Balancer - Rules(80과 443 리스너 모두 확인)
- Target Groups - Group Details(헬스 체크 경로 확인)
- Target Groups - Targets(3개 대상 모두 정상인지 확인)
 
## 단계-03: 새로 등록한 DNS 이름으로 애플리케이션 접속
- **애플리케이션 접속**
```t
# HTTP URL(HTTPS로 리디렉션되어야 함)
http://ssldemo101.stacksimplify.com/app1/index.html
http://ssldemo101.stacksimplify.com/app2/index.html
http://ssldemo101.stacksimplify.com/

# HTTPS URL
https://ssldemo101.stacksimplify.com/app1/index.html
https://ssldemo101.stacksimplify.com/app2/index.html
https://ssldemo101.stacksimplify.com/
```

## 단계-04: 정리
```t
# 매니페스트 삭제
kubectl delete -f kube-manifests/

## Route53 레코드 세트 삭제
- 생성한 Route53 레코드 삭제(ssldemo101.stacksimplify.com)
```

## 애노테이션 참고 자료
- [AWS Load Balancer Controller Annotation Reference](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/ingress/annotations/)


