---
title: AWS Load Balancer Controller - Ingress SSL 호스트 디스커버리
description: AWS Load Balancer Controller - Ingress SSL 호스트 디스커버리 학습
---

## 단계-01: 소개
- `spec.rules.host`를 사용해 AWS Certificate Manager에서 SSL 인증서를 자동으로 탐지합니다.
- 지정한 도메인 이름에 대해 ACM에 SSL 인증서가 있으면 해당 인증서가 자동으로 감지되어 ALB에 연결됩니다.
- SSL 인증서 ARN을 가져와 Kubernetes Ingress 매니페스트에 넣을 필요가 없습니다.
- Ingress 규칙의 host를 통해 `app102.stacksimplify.com` 또는 `*.stacksimplify.com` 인증서를 ALB에 자동으로 연결합니다.

## 단계-02: Ingress "spec.rules.host"로 인증서 탐지
```yaml
# Annotations Reference: https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-certdiscoveryhost-demo
  annotations:
    # Load Balancer Name
    alb.ingress.kubernetes.io/load-balancer-name: certdiscoveryhost-ingress
    # Ingress Core Settings
    #kubernetes.io/ingress.class: "alb" (OLD INGRESS CLASS NOTATION - STILL WORKS BUT RECOMMENDED TO USE IngressClass Resource)
    alb.ingress.kubernetes.io/scheme: internet-facing
    # Health Check Settings
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP 
    alb.ingress.kubernetes.io/healthcheck-port: traffic-port
    #Important Note:  Need to add health check path annotations in service level if we are planning to use multiple targets in a load balancer    
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthy-threshold-count: '2'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'   
    ## SSL Settings
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}, {"HTTP":80}]'
    #alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:180789647333:certificate/632a3ff6-3f6d-464c-9121-b9d97481a76b
    #alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-1-2017-01 #Optional (Picks default if not used)    
    # SSL Redirect Setting
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    # External DNS - For creating a Record Set in Route53
    external-dns.alpha.kubernetes.io/hostname: default102.stacksimplify.com 
spec:
  ingressClassName: alb   # Ingress Class                  
  defaultBackend:
    service:
      name: app3-nginx-nodeport-service
      port:
        number: 80     
  rules:
    - host: app102.stacksimplify.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app1-nginx-nodeport-service
                port: 
                  number: 80
    - host: app202.stacksimplify.com
      http:
        paths:                  
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app2-nginx-nodeport-service
                port: 
                  number: 80

# 중요-1: 경로 기반 라우팅에서는 순서가 매우 중요합니다. "/*"를 사용할 경우 모든 규칙의 마지막에 배치하세요.
                        
# 1. "spec.ingressClassName: alb"가 지정되지 않으면 이 쿠버네티스 클러스터의 기본 ingress class를 참조합니다.
# 2. 기본 Ingress class는 `ingressclass.kubernetes.io/is-default-class: "true"` 애노테이션이 있는 ingress class입니다.
```


## 단계-03: 애플리케이션 Kubernetes 매니페스트 배포 및 확인
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
- **중점 확인: ALB에 인증서가 연결되었는지 확인**

### External DNS 로그 확인
```t
# External DNS 로그 확인
kubectl logs -f $(kubectl get po | egrep -o 'external-dns[A-Za-z0-9-]+')
```
### Route53 확인
- Services -> Route53로 이동
- 다음 **Record Sets**가 추가되었는지 확인
  - default102.stacksimplify.com
  - app102.stacksimplify.com
  - app202.stacksimplify.com

## 단계-04: 새로 등록한 DNS 이름으로 애플리케이션 접속
### 접속 전에 nslookup 테스트 수행
- 새 DNS 엔트리가 등록되어 IP 주소로 해석되는지 확인합니다.
```t
# nslookup 명령
nslookup default102.stacksimplify.com
nslookup app102.stacksimplify.com
nslookup app202.stacksimplify.com
```
### 정상 케이스: DNS 도메인으로 애플리케이션 접속
```t
# App1 접속
http://app102.stacksimplify.com/app1/index.html

# App2 접속
http://app202.stacksimplify.com/app2/index.html

# 기본 앱(App3) 접속
http://default102.stacksimplify.com
```

## 단계-05: 정리
```t
# 매니페스트 삭제
kubectl delete -f kube-manifests/

## Route53 Record Set 확인( DNS 레코드 삭제 확인 )
- Route53 -> Hosted Zones -> Records로 이동
- 아래 레코드가 자동으로 삭제되어야 합니다.
  - default102.stacksimplify.com
  - app102.stacksimplify.com
  - app202.stacksimplify.com
```


## 참고 자료
- https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/ingress/cert_discovery/
