---
title: AWS Load Balancer Controller - 내부 NLB
description: Kubernetes로 내부 AWS Network Load Balancer를 생성하는 방법 학습
---

## 단계-01: 소개
- 내부 NLB 생성
- NLB Service K8s 매니페스트에서 `aws-load-balancer-scheme` 애노테이션을 `internal`로 설정
- curl 파드 배포
- curl 파드에 접속해 `curl` 명령으로 내부 NLB 엔드포인트 접근


## 단계-02: LB 스킴 애노테이션 검토
- **파일 이름:** `kube-manifests\\02-LBC-NLB-LoadBalancer-Service.yml`
```yaml
    # Access Control
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
```

## 단계-03: kube-manifests 전체 배포
```t
# kube-manifests 배포
kubectl apply -f kube-manifests/

# 파드 확인
kubectl get pods

# 서비스 확인
kubectl get svc
관찰 사항:
1. 네트워크 LB DNS 이름 확인

# AWS Load Balancer Controller 파드 로그 확인
kubectl -n kube-system get pods
kubectl -n kube-system logs -f <aws-load-balancer-controller-POD-NAME>

# AWS 관리 콘솔에서 확인
Services -> EC2 -> Load Balancing -> Load Balancers로 이동
1. Description 탭에서 "kubectl get svc" External IP와 일치하는 DNS Name 확인
2. Listeners 탭 확인
관찰 사항: 포트 80의 리스너 2개가 보여야 합니다.

Services -> EC2 -> Load Balancing -> Target Groups로 이동
1. 등록된 대상 확인
2. Health Check 경로 확인
```

## 단계-04: curl 파드 배포 및 내부 NLB 테스트
```t
# curl-pod 배포
kubectl apply -f kube-manifests-curl

# 컨테이너에 터미널 세션을 엽니다.
kubectl exec -it curl-pod -- sh

# 이제 외부 주소 또는 내부 서비스에 curl을 사용할 수 있습니다.
curl http://google.com/
curl <INTERNAL-NETWORK-LB-DNS>

# 내부 Network LB Curl 테스트
curl lbc-network-lb-internal-demo-7031ade4ca457080.elb.ap-northeast-2.amazonaws.com
```


## 단계-05: 정리
```t
# kube-manifests 삭제 또는 언배포
kubectl delete -f kube-manifests/
kubectl delete -f kube-manifests-curl/

# NLB 삭제 여부 확인
AWS 관리 콘솔에서,
Services -> EC2 -> Load Balancing -> Load Balancers로 이동
```

## 참고 자료
- [Network Load Balancer](https://docs.aws.amazon.com/eks/latest/userguide/network-load-balancing.html)
- [NLB Service](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/service/nlb/)
- [NLB Service Annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/service/annotations/)

