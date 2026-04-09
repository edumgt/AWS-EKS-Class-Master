---
title: AWS Load Balancer Controller - Ingress 타깃 타입 IP
description: AWS Load Balancer Controller - Ingress 타깃 타입 IP 학습
---

## 단계-01: 소개
- `alb.ingress.kubernetes.io/target-type`는 파드로 트래픽을 라우팅하는 방식을 지정합니다.
- `instance`와 `ip` 중에서 선택할 수 있습니다.
- **Instance 모드:** 서비스의 NodePort를 통해 클러스터 내 모든 EC2 인스턴스로 트래픽을 라우팅합니다.
- **IP 모드:** ALB에서 스티키 세션을 사용하려면 `ip` 모드가 필요합니다.


## 단계-02: Ingress 매니페스트 - target-type 추가
- **파일 이름:** 04-ALB-Ingress-target-type-ip.yml
```yaml
    # Target Type: IP
    alb.ingress.kubernetes.io/target-type: ip   
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
- **중점 확인: NodePort 워커 노드 IP가 아니라 파드 IP가 Target Group에 포함되어야 합니다.**
```t
# 파드 및 IP 목록
kubectl get pods -o wide
```

### External DNS 로그 확인
```t
# External DNS 로그 확인
kubectl logs -f $(kubectl get po | egrep -o 'external-dns[A-Za-z0-9-]+')
```
### Route53 확인
- Services -> Route53로 이동
- 다음 **Record Sets**가 추가되었는지 확인
  - target-type-ip-501.stacksimplify.com 


## 단계-04: 새로 등록한 DNS 이름으로 애플리케이션 접속
### 접속 전에 nslookup 테스트 수행
- 새 DNS 엔트리가 등록되어 IP 주소로 해석되는지 확인합니다.
```t
# nslookup 명령
nslookup target-type-ip-501.stacksimplify.com 
```
### DNS 도메인으로 애플리케이션 접속
```t
# App1 접속
http://target-type-ip-501.stacksimplify.com /app1/index.html

# App2 접속
http://target-type-ip-501.stacksimplify.com /app2/index.html

# 기본 앱(App3) 접속
http://target-type-ip-501.stacksimplify.com 
```

## 단계-05: 정리
```t
# 매니페스트 삭제
kubectl delete -f kube-manifests/

## Route53 Record Set 확인( DNS 레코드 삭제 확인 )
- Route53 -> Hosted Zones -> Records로 이동
- 아래 레코드가 자동으로 삭제되어야 합니다.
  - target-type-ip-501.stacksimplify.com 
```
