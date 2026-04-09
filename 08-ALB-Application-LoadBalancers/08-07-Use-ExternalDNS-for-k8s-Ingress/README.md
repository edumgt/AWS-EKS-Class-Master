---
title: AWS Load Balancer Controller - External DNS & Ingress
description: AWS Load Balancer Controller - External DNS & Ingress 학습
---

## 단계-01: External DNS 애노테이션을 추가해 Ingress 매니페스트 업데이트
- 두 개의 DNS 이름으로 애노테이션 추가
  - dnstest901.kubeoncloud.com
  - dnstest902.kubeoncloud.com
- 애플리케이션 배포 후 두 DNS 이름 모두로 접속할 수 있어야 합니다.
- **파일 이름:** 04-ALB-Ingress-SSL-Redirect-ExternalDNS.yml
```yaml
    # External DNS - For creating a Record Set in Route53
    external-dns.alpha.kubernetes.io/hostname: dnstest901.stacksimplify.com, dnstest902.stacksimplify.com
```
- 본인 환경에서는 `yourdomain`을 자신의 도메인으로 바꿉니다.
  - dnstest901.yourdoamin.com
  - dnstest902.yourdoamin.com

## 단계-02: 애플리케이션 Kubernetes 매니페스트 배포
### 배포
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

### External DNS 로그 확인
```t
# External DNS 로그 확인
kubectl logs -f $(kubectl get po | egrep -o 'external-dns[A-Za-z0-9-]+')
```
### Route53 확인
- Services -> Route53로 이동
- `dnstest901.stacksimplify.com`, `dnstest902.stacksimplify.com`의 **Record Sets**가 추가되었는지 확인

## 단계-04: 새로 등록한 DNS 이름으로 애플리케이션 접속
### 접속 전에 nslookup 테스트 수행
- 새 DNS 엔트리가 등록되어 IP 주소로 해석되는지 확인합니다.
```t
# nslookup 명령
nslookup dnstest901.stacksimplify.com
nslookup dnstest902.stacksimplify.com
```
### dnstest1 도메인으로 애플리케이션 접속
```t
# HTTP URL(HTTPS로 리디렉션되어야 함)
http://dnstest901.stacksimplify.com/app1/index.html
http://dnstest901.stacksimplify.com/app2/index.html
http://dnstest901.stacksimplify.com/
```

### dnstest2 도메인으로 애플리케이션 접속
```t
# HTTP URL(HTTPS로 리디렉션되어야 함)
http://dnstest902.stacksimplify.com/app1/index.html
http://dnstest902.stacksimplify.com/app2/index.html
http://dnstest902.stacksimplify.com/
```


## 단계-05: 정리
```t
# 매니페스트 삭제
kubectl delete -f kube-manifests/

## Route53 Record Set 확인( DNS 레코드 삭제 확인 )
- Route53 -> Hosted Zones -> Records로 이동
- 아래 레코드가 자동으로 삭제되어야 합니다.
  - dnstest901.stacksimplify.com
  - dnstest902.stacksimplify.com
```


## 참고 자료
- https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/alb-ingress.md
- https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md

