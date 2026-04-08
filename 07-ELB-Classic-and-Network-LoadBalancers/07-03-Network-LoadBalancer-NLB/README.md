# AWS - 네트워크 로드 밸런서 - NLB

## 단계-01: AWS 네트워크 로드 밸런서 Kubernetes 매니페스트 생성 및 배포
- **04-NetworkLoadBalancer.yml**
```yml
apiVersion: v1
kind: Service
metadata:
  name: nlb-usermgmt-restapp
  labels:
    app: usermgmt-restapp
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb    # 네트워크 로드 밸런서 생성
spec:
  type: LoadBalancer # 일반적인 k8s Service 매니페스트에서 type을 LoadBalancer로 설정
  selector:
    app: usermgmt-restapp     
  ports:
  - port: 80
    targetPort: 8095
```

---
```
service.beta.kubernetes.io/aws-load-balancer-type: nlb 는 Kubernetes Service(Type=LoadBalancer) 를 만들 때 AWS에서 Network Load Balancer(NLB) 로 생성하라고 지시하는 어노테이션이에요.

아래는 NLB vs CLB(Classic Load Balancer) 핵심 차이입니다.

NLB (Network Load Balancer)

L4(전송 계층) 기반: TCP/UDP/TLS 같은 “연결/포트” 수준으로 분산 (HTTP 경로 기반 라우팅 같은 L7 기능은 기본적으로 아님)

초고성능/저지연: 대규모 트래픽 처리에 유리(네트워크 레벨에서 매우 빠르게 처리)

클라이언트 원본 IP 보존이 쉬움: 백엔드에서 실제 사용자 IP를 보아야 하는 요구(로그/보안/레이트리밋)에 유리

고정 IP(EIP) 요구에 유리: AZ별 고정 IP 같은 구성 시나리오에서 자주 선택

EKS에서 Service로 외부 노출할 때 대표 선택지(특히 TCP/UDP 서비스)

CLB (Classic Load Balancer)

레거시(구세대) 로드밸런서: 예전(EC2 Classic 시절)부터 쓰던 타입으로, 요즘은 신규 설계에서 ALB/NLB로 대체하는 흐름이 일반적

기능/확장성 측면에서 제한: 최신 로드밸런서들(ALB/NLB)이 제공하는 여러 개선점(유연한 타겟, 고급 기능 등) 대비 선택 이유가 줄어듦

EKS 관점에서도 “가능은 하지만” 보통은 NLB(네트워크) 또는 ALB(HTTP/HTTPS)로 가는 게 표준에 가까움

언제 NLB를 쓰고, 언제 CLB를 쓰나?

NLB 추천

서비스가 TCP/UDP 기반(예: gRPC over TCP, 게임/소켓, DB 프록시 등)

성능/지연이 민감

원본 IP 보존, 고정 IP/EIP 같은 네트워크 요구가 있음

CLB는 보통 “기존에 이미 CLB로 운영 중인 레거시” 를 유지해야 할 때 정도가 주된 이유

(중요) HTTP/HTTPS “규칙 기반 라우팅”이 필요하면?

URL 경로(/api, /web), Host 기반 같은 L7 라우팅이 목적이면 보통 NLB/CLB가 아니라 ALB + Ingress(AWS Load Balancer Controller) 를 씁니다.
```
---

- **모든 매니페스트 배포**
```
# 모든 매니페스트 배포
kubectl apply -f kube-manifests/

# 서비스 목록 조회 (새로 생성된 NLB 서비스 확인)
kubectl get svc

# 파드 확인
kubectl get pods
```

## 단계-02: 배포 확인
- 새로운 NLB가 생성되었는지 확인
  - Services -> EC2 -> Load Balancing -> Load Balancers 로 이동
    - NLB가 생성되어 있어야 함
    - DNS 이름 복사 (예: a85ae6e4030aa4513bd200f08f1eb9cc-7f13b3acc1bcaaa2.elb.ap-northeast-2.amazonaws.com)
  - Services -> EC2 -> Load Balancing -> Target Groups 로 이동
    - 헬스 상태를 확인하고 active 상태인지 확인
- **애플리케이션 접속**
```
# 애플리케이션 접속
http://<NLB-DNS-NAME>/usermgmt/health-status
```    

## 단계-03: 정리
```
# 생성된 모든 오브젝트 삭제
kubectl delete -f kube-manifests/

# 현재 Kubernetes 오브젝트 확인
kubectl get all
```
