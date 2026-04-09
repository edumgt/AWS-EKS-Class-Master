---
title: AWS Load Balancer Ingress 컨텍스트 경로 기반 라우팅
description: AWS Load Balancer Controller - Ingress 컨텍스트 경로 기반 라우팅 학습
---

## 단계-01: 소개
- 이 섹션에서 구축할 아키텍처를 논의합니다.
- Ingress Controller에서 컨텍스트 경로 기반 라우팅을 활성화해 Kubernetes에 3개 앱을 배포합니다.
  - /app1/* - app1-nginx-nodeport-service로 라우팅
  - /app2/* - app1-nginx-nodeport-service로 라우팅
  - /*    - app3-nginx-nodeport-service로 라우팅
- 이 과정에서 `alb.ingress.kubernetes.io/healthcheck-path:` 애노테이션을 각 앱의 NodePort Service로 이동합니다.
- `04-ALB-Ingress-ContextPath-Based-Routing.yml`의 Ingress 매니페스트 애노테이션에는 공통 설정만 유지합니다.


## 단계-02: Nginx App1, App2, App3 Deployment 및 Service 검토
- 3개 앱의 차이는 Kubernetes 매니페스트 관점에서 2개 필드와 네이밍 컨벤션뿐입니다.
  - **Kubernetes Deployment:** 컨테이너 이미지 이름
  - **Kubernetes Node Port Service:** 헬스 체크 URL 경로
- **App1 Nginx: 01-Nginx-App1-Deployment-and-NodePortService.yml**
  - **image:** stacksimplify/kube-nginxapp1:1.0.0
  - **Annotation:** alb.ingress.kubernetes.io/healthcheck-path: /app1/index.html
- **App2 Nginx: 02-Nginx-App2-Deployment-and-NodePortService.yml**
  - **image:** stacksimplify/kube-nginxapp2:1.0.0
  - **Annotation:** alb.ingress.kubernetes.io/healthcheck-path: /app2/index.html
- **App3 Nginx: 03-Nginx-App3-Deployment-and-NodePortService.yml**
  - **image:** stacksimplify/kubenginx:1.0.0
  - **Annotation:** alb.ingress.kubernetes.io/healthcheck-path: /index.html



## 단계-03: ALB Ingress 컨텍스트 경로 기반 라우팅 매니페스트 생성
- **04-ALB-Ingress-ContextPath-Based-Routing.yml**
```yaml
# Annotations Reference: https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-cpr-demo
  annotations:
    # Load Balancer Name
    alb.ingress.kubernetes.io/load-balancer-name: cpr-ingress
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
spec:
  ingressClassName: alb   # Ingress Class                  
  rules:
    - http:
        paths:      
          - path: /app1
            pathType: Prefix
            backend:
              service:
                name: app1-nginx-nodeport-service
                port: 
                  number: 80
          - path: /app2
            pathType: Prefix
            backend:
              service:
                name: app2-nginx-nodeport-service
                port: 
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app3-nginx-nodeport-service
                port: 
                  number: 80              

# 중요-1: 경로 기반 라우팅에서는 순서가 매우 중요합니다. "/*"를 사용할 경우 모든 규칙의 마지막에 배치하세요.
                        
# 1. "spec.ingressClassName: alb"가 지정되지 않으면 이 쿠버네티스 클러스터의 기본 ingress class를 참조합니다.
# 2. 기본 Ingress class는 `ingressclass.kubernetes.io/is-default-class: "true"` 애노테이션이 있는 ingress class입니다.
```

## 단계-04: 모든 매니페스트 배포 및 테스트
```t
# Kubernetes 매니페스트 배포
kubectl apply -f kube-manifests/

# 파드 목록
kubectl get pods

# 서비스 목록
kubectl get svc

# Ingress 로드 밸런서 목록
kubectl get ingress

# Ingress 상세 확인 및 규칙 보기
kubectl describe ingress ingress-cpr-demo

# AWS Load Balancer Controller 로그 확인
kubectl -n kube-system  get pods 
kubectl -n kube-system logs -f aws-load-balancer-controller-794b7844dd-8hk7n 
```

## 단계-05: AWS 관리 콘솔에서 Application Load Balancer 확인
- 로드 밸런서 확인
    - Listeners 탭에서 Rules 아래 **View/Edit Rules** 클릭
- Target Groups 확인
    - GroupD Details 확인
    - Targets: 정상(Healthy) 상태 확인
    - 헬스 체크 경로 확인
    - 3개 대상이 모두 정상인지 확인
```t
# 애플리케이션 접속
http://<ALB-DNS-URL>/app1/index.html
http://<ALB-DNS-URL>/app2/index.html
http://<ALB-DNS-URL>/
```

## 단계-06: 컨텍스트 경로 기반 라우팅의 순서 테스트
### 단계-06-01: 루트 컨텍스트 경로를 상단으로 이동
- **File:** 04-ALB-Ingress-ContextPath-Based-Routing.yml
```yaml
  ingressClassName: alb   # Ingress Class                  
  rules:
    - http:
        paths:      
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app3-nginx-nodeport-service
                port: 
                  number: 80           
          - path: /app1
            pathType: Prefix
            backend:
              service:
                name: app1-nginx-nodeport-service
                port: 
                  number: 80
          - path: /app2
            pathType: Prefix
            backend:
              service:
                name: app2-nginx-nodeport-service
                port: 
                  number: 80
```
### 단계-06-02: 변경 사항 배포 및 확인
```t
# 변경 사항 배포
kubectl apply -f kube-manifests/

# 애플리케이션 접속(새 시크릿 창에서 열기)
http://<ALB-DNS-URL>/app1/index.html  -- SHOULD FAIL
http://<ALB-DNS-URL>/app2/index.html  -- SHOULD FAIL
http://<ALB-DNS-URL>/  - SHOULD PASS
```

## 단계-07: 04-ALB-Ingress-ContextPath-Based-Routing.yml 변경 사항 롤백
```yaml
spec:
  ingressClassName: alb   # Ingress Class                  
  rules:
    - http:
        paths:      
          - path: /app1
            pathType: Prefix
            backend:
              service:
                name: app1-nginx-nodeport-service
                port: 
                  number: 80
          - path: /app2
            pathType: Prefix
            backend:
              service:
                name: app2-nginx-nodeport-service
                port: 
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app3-nginx-nodeport-service
                port: 
                  number: 80              
```

## 단계-08: 정리
```t
# 정리
kubectl delete -f kube-manifests/
```
