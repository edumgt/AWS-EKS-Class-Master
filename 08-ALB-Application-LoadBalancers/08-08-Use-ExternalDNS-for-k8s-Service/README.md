---
title: AWS Load Balancer Controller - External DNS & Service
description: AWS Load Balancer Controller - External DNS & Kubernetes Service 학습
---

## 단계-01: 소개
- `type: LoadBalancer`의 Kubernetes Service를 생성합니다.
- Service에 `external-dns.alpha.kubernetes.io/hostname: externaldns-k8s-service-demo101.stacksimplify.com` 애노테이션을 추가해 해당 로드 밸런서 DNS를 Route53에 등록합니다.

## Step-02: 02-Nginx-App1-LoadBalancer-Service.yml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: app1-nginx-loadbalancer-service
  labels:
    app: app1-nginx
  annotations:
    external-dns.alpha.kubernetes.io/hostname: externaldns-k8s-service-demo101.stacksimplify.com
spec:
  type: LoadBalancer
  selector:
    app: app1-nginx
  ports:
    - port: 80
      targetPort: 80  
```
## 단계-03: 배포 및 확인

### 배포 및 확인
```t
# kube-manifests 배포
kubectl apply -f kube-manifests/

# 앱 확인
kubectl get deploy
kubectl get pods

# 서비스 확인
kubectl get svc
```
### Load Balancer 확인
- EC2 -> Load Balancers로 이동해 로드 밸런서 설정 확인

### External DNS 로그 확인
```t
# External DNS 로그 확인
kubectl logs -f $(kubectl get po | egrep -o 'external-dns[A-Za-z0-9-]+')
```
### Route53 확인
- Services -> Route53로 이동
- `externaldns-k8s-service-demo101.stacksimplify.com`에 대한 **Record Sets**가 추가되었는지 확인


## 단계-04: 새로 등록한 DNS 이름으로 애플리케이션 접속
### 접속 전에 nslookup 테스트 수행
- 새 DNS 엔트리가 등록되어 IP 주소로 해석되는지 확인합니다.
```t
# nslookup 명령
nslookup externaldns-k8s-service-demo101.stacksimplify.com
```
### DNS 도메인으로 애플리케이션 접속
```t
# HTTP URL
http://externaldns-k8s-service-demo101.stacksimplify.com/app1/index.html
```

## 단계-05: 정리
```t
# 매니페스트 삭제
kubectl delete -f kube-manifests/

## Route53 Record Set 확인( DNS 레코드 삭제 확인 )
- Route53 -> Hosted Zones -> Records로 이동
- 아래 레코드가 자동으로 삭제되어야 합니다.
  - externaldns-k8s-service-demo101.stacksimplify.com
```


## 참고 자료
- https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/alb-ingress.md
- https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
