---
title: AWS Load Balancer Ingress SSL
description: AWS Load Balancer Controller - Ingress SSL 학습
---

## 단계-01: 소개
- AWS Route53에 새 DNS를 등록합니다.
- SSL 인증서를 생성합니다.
- Ingress 매니페스트에 SSL 인증서 관련 애노테이션을 추가합니다.
- 매니페스트를 배포하고 테스트합니다.
- 정리합니다.

## 단계-02: 사전 준비 - Route53에 도메인 등록(없다면)
- Services -> Route53 -> Registered Domains로 이동
- **Register Domain** 클릭
- **desired domain: somedomain.com** 입력 후 **check** 클릭(예: `stacksimplify.com`)
- **Add to cart** 클릭 후 **Continue**
- **Contact Details** 입력 후 **Continue**
- Automatic Renewal 활성화
- **Terms and Conditions** 동의
- **Complete Order** 클릭

## 단계-03: Certificate Manager에서 SSL 인증서 생성
- 사전 조건: Route53에 등록된 도메인이 있어야 합니다.
- Services -> Certificate Manager -> Create a Certificate로 이동
- **Request a Certificate** 클릭
  - ACM에서 제공할 인증서 유형 선택: Request a public certificate
  - 도메인 이름 추가: *.yourdomain.com(예: `*.stacksimplify.com`)
  - 검증 방법 선택: **DNS Validation**
  - **Confirm & Request** 클릭
- **Validation**
  - **Create record in Route 53** 클릭
- 5~10분 대기 후 **Validation Status** 확인

## 단계-04: SSL 관련 애노테이션 추가
- **04-ALB-Ingress-SSL.yml**
```yaml
    ## SSL Settings
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}, {"HTTP":80}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:180789647333:certificate/632a3ff6-3f6d-464c-9121-b9d97481a76b
    #alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-1-2017-01 #Optional (Picks default if not used)    
```
## 단계-05: 모든 매니페스트 배포 및 테스트
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

## 단계-06: Route53에 DNS 추가
- **Services -> Route 53**로 이동
- **Hosted Zones**로 이동
  - **yourdomain.com** 클릭(예: stacksimplify.com)
- **Record Set** 생성
  - **Name:** ssldemo101.stacksimplify.com
  - **Alias:** yes
  - **Alias Target:** ALB DNS 이름 복사(예: ssl-ingress-551932098.ap-northeast-2.elb.amazonaws.com)
  - **Create** 클릭
  
## 단계-07: 새로 등록한 DNS 이름으로 애플리케이션 접속
- **애플리케이션 접속**
- **중요:** `stacksimplify.com` 대신 Route53에 등록한 도메인으로 바꿔야 합니다(사전 준비 단계-02 참고).
```t
# HTTP URL
http://ssldemo101.stacksimplify.com/app1/index.html
http://ssldemo101.stacksimplify.com/app2/index.html
http://ssldemo101.stacksimplify.com/

# HTTPS URL
https://ssldemo101.stacksimplify.com/app1/index.html
https://ssldemo101.stacksimplify.com/app2/index.html
https://ssldemo101.stacksimplify.com/
```

## 애노테이션 참고 자료
- [AWS Load Balancer Controller Annotation Reference](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/ingress/annotations/)
