---
title: AWS Load Balancer Controller - Ingress 그룹
description: AWS Load Balancer Controller - Ingress 그룹 학습
---

## 단계-01: 소개
- IngressGroup 기능은 여러 Ingress 리소스를 그룹으로 묶을 수 있게 해줍니다.
- 컨트롤러는 IngressGroup 내 모든 Ingress 규칙을 자동으로 병합하여 하나의 ALB로 제공합니다.
- 또한 대부분의 Ingress 애노테이션은 해당 Ingress에 정의된 경로에만 적용됩니다.
- 두 개의 애플리케이션으로 Ingress 그룹 개념을 시연합니다.

## 단계-02: App1 Ingress 매니페스트 핵심 라인 검토
- **파일 이름:** `kube-manifests/app1/02-App1-Ingress.yml`
```yaml
    # Ingress Groups
    alb.ingress.kubernetes.io/group.name: myapps.web
    alb.ingress.kubernetes.io/group.order: '10'
```

## 단계-03: App2 Ingress 매니페스트 핵심 라인 검토
- **파일 이름:** `kube-manifests/app2/02-App2-Ingress.yml`
```yaml
    # Ingress Groups
    alb.ingress.kubernetes.io/group.name: myapps.web
    alb.ingress.kubernetes.io/group.order: '20'
```

## 단계-04: App3 Ingress 매니페스트 핵심 라인 검토
```yaml
    # Ingress Groups
    alb.ingress.kubernetes.io/group.name: myapps.web
    alb.ingress.kubernetes.io/group.order: '30'
```

## 단계-05: 두 개의 Ingress 리소스로 앱 배포
```t
# 두 앱 배포
kubectl apply -R -f kube-manifests

# 파드 확인
kubectl get pods

# Ingress 확인
kubectl  get ingress
관찰 사항:
1. 동일한 ADDRESS 값을 가진 3개의 Ingress 리소스가 생성됩니다.
2. 동일한 Ingress 그룹 "myapps.web"에 속하므로 3개의 Ingress 리소스가 하나의 ALB로 병합됩니다.
```

## 단계-06: AWS 관리 콘솔에서 확인
- Services -> EC2 -> Load Balancers로 이동
- `/app1`, `/app2` 및 `default backend` 라우팅 규칙 확인

## 단계-07: 브라우저에서 접속 확인
```t
# 웹 URL
http://ingress-groups-demo601.stacksimplify.com/app1/index.html
http://ingress-groups-demo601.stacksimplify.com/app2/index.html
http://ingress-groups-demo601.stacksimplify.com
```

## 단계-08: 정리
```t
# K8s 클러스터에서 앱 삭제
kubectl delete -R -f kube-manifests/

## Route53 Record Set 확인( DNS 레코드 삭제 확인 )
- Route53 -> Hosted Zones -> Records로 이동
- 아래 레코드가 자동으로 삭제되어야 합니다.
  - ingress-groups-demo601.stacksimplify.com
```
