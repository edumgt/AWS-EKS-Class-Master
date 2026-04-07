---
title: AWS Load Balancer Controller - Ingress 기본
description: AWS Load Balancer Controller - Ingress 기본 학습
---

## 단계-01: 소개
- 배포할 애플리케이션 아키텍처를 논의합니다.
- 다음 Ingress 개념을 이해합니다.
  - [Annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/)
  - [ingressClassName](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/ingress_class/)
  - defaultBackend
  - rules

## 단계-02: App1 Deployment kube-manifest 검토
- **파일 위치:** `01-kube-manifests-default-backend/01-Nginx-App1-Deployment-and-NodePortService.yml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app1-nginx-deployment
  labels:
    app: app1-nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app1-nginx
  template:
    metadata:
      labels:
        app: app1-nginx
    spec:
      containers:
        - name: app1-nginx
          image: stacksimplify/kube-nginxapp1:1.0.0
          ports:
            - containerPort: 80
```
## 단계-03: App1 NodePort Service 검토
- **파일 위치:** `01-kube-manifests-default-backend/01-Nginx-App1-Deployment-and-NodePortService.yml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: app1-nginx-nodeport-service
  labels:
    app: app1-nginx
  annotations:
#Important Note:  Need to add health check path annotations in service level if we are planning to use multiple targets in a load balancer    
#    alb.ingress.kubernetes.io/healthcheck-path: /app1/index.html
spec:
  type: NodePort
  selector:
    app: app1-nginx
  ports:
    - port: 80
      targetPort: 80  
```

## 단계-04: Default Backend 옵션이 있는 Ingress kube-manifest 검토
- [Annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/)
- **파일 위치:** `01-kube-manifests-default-backend/02-ALB-Ingress-Basic.yml`
```yaml
# Annotations Reference: https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-nginxapp1
  labels:
    app: app1-nginx
  annotations:
    #kubernetes.io/ingress.class: "alb" (OLD INGRESS CLASS NOTATION - STILL WORKS BUT RECOMMENDED TO USE IngressClass Resource)
    # Ingress Core Settings
    alb.ingress.kubernetes.io/scheme: internet-facing
    # Health Check Settings
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP 
    alb.ingress.kubernetes.io/healthcheck-port: traffic-port
    alb.ingress.kubernetes.io/healthcheck-path: /app1/index.html    
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthy-threshold-count: '2'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'
spec:
  ingressClassName: alb # Ingress Class
  defaultBackend:
    service:
      name: app1-nginx-nodeport-service
      port:
        number: 80                    
```

## 단계-05: kube-manifests 배포 및 확인
```t
# 디렉터리 이동
cd 08-02-ALB-Ingress-Basics

# kube-manifests 배포
kubectl apply -f 01-kube-manifests-default-backend/

# K8s Deployment 및 파드 확인
kubectl get deploy
kubectl get pods

# Ingress 확인(ADDRESS 필드 기록)
kubectl get ingress
관찰 사항:
1. ADDRESS 값을 확인합니다. 예) "app1ingress-1334515506.us-east-1.elb.amazonaws.com"

# Ingress Controller 설명 확인
kubectl describe ingress ingress-nginxapp1
관찰 사항:
1. Default Backend 및 Rules 확인

# 서비스 목록
kubectl get svc

# Application Load Balancer 확인
AWS 관리 콘솔 -> Services -> EC2 -> Load Balancers로 이동
1. 리스너 내부의 리스너 및 규칙 확인
2. Target Groups 확인

# 브라우저로 앱 접속
kubectl get ingress
http://<ALB-DNS-URL>
http://<ALB-DNS-URL>/app1/index.html
or
http://<INGRESS-ADDRESS-FIELD>
http://<INGRESS-ADDRESS-FIELD>/app1/index.html

# 내 환경 예시(참고용)
http://app1ingress-154912460.us-east-1.elb.amazonaws.com
http://app1ingress-154912460.us-east-1.elb.amazonaws.com/app1/index.html

# AWS Load Balancer Controller 로그 확인
kubectl get po -n kube-system 
## POD1 Logs: 
kubectl -n kube-system logs -f <POD1-NAME>
kubectl -n kube-system logs -f aws-load-balancer-controller-65b4f64d6c-h2vh4
##POD2 Logs: 
kubectl -n kube-system logs -f <POD2-NAME>
kubectl -n kube-system logs -f aws-load-balancer-controller-65b4f64d6c-t7qqb
```

## 단계-06: 정리
```t
# Kubernetes 리소스 삭제
kubectl delete -f 01-kube-manifests-default-backend/
```

## 단계-07: Ingress Rules가 있는 Ingress kube-manifest 검토
- [Ingress Path Types](https://kubernetes.io/docs/concepts/services-networking/ingress/#path-types) 논의
- [Better Path Matching With Path Types](https://kubernetes.io/blog/2020/04/02/improvements-to-the-ingress-api-in-kubernetes-1.18/#better-path-matching-with-path-types)
- [Sample Ingress Rule](https://kubernetes.io/docs/concepts/services-networking/ingress/#the-ingress-resource)
- **ImplementationSpecific (기본):** 이 path type은 IngressClass 구현 컨트롤러가 매칭을 결정합니다. 구현에 따라 별도 pathType으로 처리하거나 Prefix/Exact와 동일하게 처리할 수 있습니다.
- **Exact:** URL 경로를 대소문자 구분하여 정확히 매칭합니다.
- **Prefix:** URL 경로 prefix를 `/` 기준으로 분할해 요소 단위로 매칭하며 대소문자를 구분합니다.

- **파일 위치:** `02-kube-manifests-rules\\02-ALB-Ingress-Basic.yml`
```yaml
# Annotations Reference: https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-nginxapp1
  labels:
    app: app1-nginx
  annotations:
    # Load Balancer Name
    alb.ingress.kubernetes.io/load-balancer-name: app1ingressrules
    #kubernetes.io/ingress.class: "alb" (OLD INGRESS CLASS NOTATION - STILL WORKS BUT RECOMMENDED TO USE IngressClass Resource)
    # Ingress Core Settings
    alb.ingress.kubernetes.io/scheme: internet-facing
    # Health Check Settings
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP 
    alb.ingress.kubernetes.io/healthcheck-port: traffic-port
    alb.ingress.kubernetes.io/healthcheck-path: /app1/index.html    
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthy-threshold-count: '2'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'
spec:
  ingressClassName: alb # Ingress Class
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app1-nginx-nodeport-service
                port: 
                  number: 80
      

# 1. "spec.ingressClassName: alb"가 지정되지 않으면 이 쿠버네티스 클러스터의 기본 ingress class를 참조합니다.
# 2. 기본 Ingress class는 `ingressclass.kubernetes.io/is-default-class: "true"` 애노테이션이 있는 ingress class입니다.
```

## 단계-08: kube-manifests 배포 및 확인
```t
# 디렉터리 이동
cd 08-02-ALB-Ingress-Basics

# kube-manifests 배포
kubectl apply -f 02-kube-manifests-rules/

# K8s Deployment 및 파드 확인
kubectl get deploy
kubectl get pods

# Ingress 확인(ADDRESS 필드 기록)
kubectl get ingress
관찰 사항:
1. ADDRESS 값을 확인합니다. 예) "app1ingressrules-154912460.us-east-1.elb.amazonaws.com"

# Ingress Controller 설명 확인
kubectl describe ingress ingress-nginxapp1
관찰 사항:
1. Default Backend 및 Rules 확인

# 서비스 목록
kubectl get svc

# Application Load Balancer 확인
AWS 관리 콘솔 -> Services -> EC2 -> Load Balancers로 이동
1. 리스너 내부의 리스너 및 규칙 확인
2. Target Groups 확인

# 브라우저로 앱 접속
kubectl get ingress
http://<ALB-DNS-URL>
http://<ALB-DNS-URL>/app1/index.html
or
http://<INGRESS-ADDRESS-FIELD>
http://<INGRESS-ADDRESS-FIELD>/app1/index.html

# 내 환경 예시(참고용)
http://app1ingressrules-154912460.us-east-1.elb.amazonaws.com
http://app1ingressrules-154912460.us-east-1.elb.amazonaws.com/app1/index.html

# AWS Load Balancer Controller 로그 확인
kubectl get po -n kube-system 
kubectl logs -f aws-load-balancer-controller-794b7844dd-8hk7n -n kube-system
```



## 단계-09: 정리
```t
# Kubernetes 리소스 삭제
kubectl delete -f 02-kube-manifests-rules/

# Ingress가 정상적으로 삭제되었는지 확인
kubectl get ingress
중요: ALB 로드 밸런서를 제대로 삭제하지 않고 방치하면 비용이 크게 발생합니다.

# Application Load Balancer 삭제 확인
AWS 관리 콘솔 -> Services -> EC2 -> Load Balancers로 이동
```

