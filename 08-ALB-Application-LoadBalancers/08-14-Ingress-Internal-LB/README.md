---
title: AWS Load Balancer Controller - Ingress 내부 LB
description: AWS Load Balancer Controller - Ingress 내부 LB 학습
---

## 단계-01: 소개
- Ingress로 내부 Application Load Balancer를 생성합니다.
- 내부 LB 테스트를 위해 `curl-pod`를 사용합니다.
- `curl-pod` 배포
- `curl-pod`에 접속해 내부 LB를 테스트합니다.

## 단계-02: Ingress 스킴 애노테이션을 internal로 변경
- **파일 이름:** 04-ALB-Ingress-Internal-LB.yml
```yaml
    # Creates Internal Application Load Balancer
    alb.ingress.kubernetes.io/scheme: internal 
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

## 단계-04: 내부 Load Balancer 테스트 방법
- EKS 클러스터에 `curl-pod`를 배포합니다.
- `curl-pod`에 접속해 내부 Application Load Balancer로 로드 밸런싱되는 샘플 앱을 `curl` 명령으로 테스트합니다.


## 단계-05: curl-pod Kubernetes 매니페스트
- **파일 이름:** kube-manifests-curl/01-curl-pod.yml
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: curl-pod
spec:
  containers:
  - name: curl
    image: curlimages/curl 
    command: [ "sleep", "600" ]
```

## 단계-06: curl-pod 배포 및 내부 LB 확인
```t
# curl-pod 배포
kubectl apply -f kube-manifests-curl

# 컨테이너에 터미널 세션을 엽니다.
kubectl exec -it curl-pod -- sh

# 이제 외부 주소 또는 내부 서비스에 curl을 사용할 수 있습니다.
curl http://google.com/
curl internal-ingress-internal-lb-553684158.ap-northeast-2.elb.amazonaws.com

# App1 Curl 테스트
curl internal-ingress-internal-lb-553684158.ap-northeast-2.elb.amazonaws.com/app1/index.html

# App2 Curl 테스트
curl internal-ingress-internal-lb-553684158.ap-northeast-2.elb.amazonaws.com/app2/index.html

```


## 단계-07: 정리
```t
# 매니페스트 삭제
kubectl delete -f kube-manifests/
kubectl delete -f kube-manifests-curl/
```
