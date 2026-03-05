# EKS - 프라이빗 서브넷에서 EKS 노드 그룹 생성

## 단계-01: 소개
- VPC 프라이빗 서브넷에 노드 그룹을 생성합니다.
- 프라이빗 노드 그룹에 워크로드를 배포하며, 워크로드는 프라이빗 서브넷에서 실행되고 로드 밸런서는 퍼블릭 서브넷에 생성되어 인터넷에서 접근 가능합니다.

## 단계-02: EKS 클러스터의 기존 퍼블릭 노드 그룹 삭제
```
# EKS 클러스터의 노드 그룹 조회
eksctl get nodegroup --cluster=<Cluster-Name>
eksctl get nodegroup --cluster=eksdemo1

# 노드 그룹 삭제 - 노드 그룹 이름과 클러스터 이름을 교체
eksctl delete nodegroup <NodeGroup-Name> --cluster <Cluster-Name>
eksctl delete nodegroup eksdemo1-ng-public1 --cluster eksdemo1
```

## 단계-03: 프라이빗 서브넷에 EKS 노드 그룹 생성
- 클러스터에 프라이빗 노드 그룹을 생성합니다.
- 핵심 옵션은 `--node-private-networking` 입니다.

```
eksctl create cluster --name=eksdemo1 \
                      --region=ap-northeast-2 \
                      --zones=ap-northeast-2a,ap-northeast-2b \
                      --without-nodegroup 
```


```
eksctl create nodegroup --cluster=eksdemo1 \
                        --region=ap-northeast-2 \
                        --name=eksdemo1-ng-private1 \
                        --node-type=t3.medium \
                        --nodes-min=2 \
                        --nodes-max=4 \
                        --node-volume-size=20 \
                        --ssh-access \
                        --ssh-public-key=kube-demo \
                        --managed \
                        --asg-access \
                        --external-dns-access \
                        --full-ecr-access \
                        --appmesh-access \
                        --alb-ingress-access \
                        --node-private-networking                       
```

## 단계-04: 노드 그룹이 프라이빗 서브넷에 생성되었는지 확인

### 워커 노드의 External IP 주소 확인
- 워커 노드가 프라이빗 서브넷에 생성되었다면 External IP는 none이어야 합니다.
```
kubectl get nodes -o wide
```

### 서브넷 라우트 테이블 확인 - 아웃바운드 트래픽이 NAT 게이트웨이를 통과
- 노드 그룹 서브넷 라우트를 확인하여 프라이빗 서브넷에 생성되었는지 검증합니다.
  - Services -> EKS -> eksdemo -> eksdemo1-ng1-private 로 이동
  - **Details** 탭에서 Associated subnet 클릭
  - **Route Table** 탭 클릭
  - NAT 게이트웨이를 통한 인터넷 경로가 보여야 합니다(0.0.0.0/0 -> nat-xxxxxxxx)

---
# AWS IGW(Internet Gateway) vs NAT Gateway 차이 정리

## 1) 한 줄 요약
- **IGW(Internet Gateway)**: VPC의 **인터넷 출입문**. 퍼블릭 서브넷 리소스가 조건을 만족하면 **인터넷과 직접 양방향 통신** 가능
- **NAT Gateway(NAT)**: 프라이빗 서브넷 리소스가 **인터넷으로 “나가기만”** 하도록 해주는 **주소 변환 기반 중계 게이트웨이**(인바운드 신규 연결 불가)

---

## 2) IGW (Internet Gateway)
### 역할
- VPC를 인터넷과 연결하는 게이트웨이(출입문)
- 공인 IP(EIP/퍼블릭 IPv4)를 가진 리소스가 인터넷과 통신하도록 지원

### 트래픽 특성
- **아웃바운드(나감)**: 가능
- **인바운드(들어옴)**: 가능  
  (단, **보안그룹/NACL 허용** + **인스턴스 공인 IP** 등 조건이 맞아야 함)

### 일반 라우팅 예시(퍼블릭 서브넷)
- 퍼블릭 서브넷 라우팅 테이블:
  - `0.0.0.0/0 -> IGW`

---

## 3) NAT Gateway (NAT)
### 역할
- 프라이빗 서브넷 인스턴스가 **공인 IP 없이도** 외부(인터넷)로 나가서
  - OS 업데이트
  - 패키지 설치
  - 외부 API 호출
  - 컨테이너 이미지 Pull  
  등을 할 수 있게 해주는 **아웃바운드 전용 출구**

### 트래픽 특성
- **아웃바운드(나감)**: 가능
- **인바운드(들어옴)**: 기본적으로 불가  
  (외부에서 프라이빗 인스턴스로 **새 연결을 시작**하는 형태는 불가)

### 생성/구성 특징
- NAT Gateway는 **퍼블릭 서브넷**에 생성
- NAT Gateway는 **EIP(Elastic IP)** 를 붙여 인터넷과 통신
- 프라이빗 서브넷 라우팅 테이블:
  - `0.0.0.0/0 -> NAT Gateway`

> 참고: NAT Gateway도 인터넷으로 나가려면 VPC에 **IGW가 있어야** 함  
> (Private Instance → NAT GW → IGW → Internet)

---

## 4) 언제 무엇을 쓰나?
- **IGW가 필요한 경우**
  - 인터넷에서 내 서비스로 들어와야 함(예: ALB, 웹 서버 등)
- **NAT Gateway가 필요한 경우**
  - 서버는 외부에서 직접 접속되면 안 되지만
  - 밖으로만 나가야 하는 요구(업데이트/이미지 Pull/외부 API 호출 등)가 있음

---

## 5) NAT는 무슨 약자?
- **NAT = Network Address Translation**
- 한국어로는 보통 **네트워크 주소 변환**
- 내부 사설 IP의 트래픽이 인터넷으로 나갈 때 **출발지 IP를 공인 IP로 변환**하고,
  응답이 돌아오면 **원래 내부 사설 IP로 매핑**해 전달하는 방식
