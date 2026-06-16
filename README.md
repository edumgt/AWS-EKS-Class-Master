## AWS EKS Class Master

# AWS EKS Lab — Architecture

> `ARCHITECTURE.drawio` / `ARCHITECTURE.svg` 는 이 문서로 통합되었습니다.
> 현재 실제 배포 상태를 기준으로 작성된 단일 아키텍처 문서입니다.

---

## 1. 전체 구성 개요

| 구분 | eksdemo1 | eksdemo2 |
|---|---|---|
| **VPC CIDR** | `10.0.0.0/16` (신규) | `192.168.0.0/16` |
| **VPC ID** | vpc-0d929a3c7be826c6a | vpc-0a31321ddfd455d8d |
| **K8s 버전** | 1.34 | 1.34 |
| **노드그룹** | eksdemo1-ng-private1 (private, NAT) | eksdemo2 + ng-7f75f (public) |
| **인스턴스** | t3.medium × 2 | t3.medium × 3 |
| **ALB** | ecr-ingress-eksdemo1 | ecr-ingress |
| **DB** | MariaDB 11.4 on EBS (내부) | MariaDB 11.4 on EBS (내부) |
| **외부 DB 접속** | — | mariadb-nlb (NLB, internet-facing :3306) |

---

## 2. 아키텍처 다이어그램

```mermaid
flowchart TB
  User([User / Client])
  DBeaver([DBeaver])
  ECR[(ECR\naws-ecr-kubenginx:1.0.0)]

  subgraph AWS["AWS Account (086015456585) — ap-northeast-2"]

    subgraph VPC1["eksdemo1 VPC — 10.0.0.0/16"]
      direction TB
      ALB1[ALB\necr-ingress-eksdemo1\ninternet-facing]

      subgraph PUB1["Public Subnets (10.0.x.x)"]
        NAT1[NAT Gateway]
      end

      subgraph PRI1["Private Subnets (10.0.x.x)"]
        subgraph EKS1["EKS eksdemo1 (NodeGroup: private)"]
          nginx1[kubeapp-ecr Pod\nNginx:1.0.0]
          be1[usermgmt-microservice\nSpring Boot :8095]
          db1[(MariaDB 11.4\nClusterIP: mariadb:3306)]
          ebs1[EBS Volume 4Gi\nStorageClass: ebs-sc]
          db1 --- ebs1
        end
      end

      ALB1 -->|"/"| nginx1
      ALB1 -->|"/usermgmt"| be1
      be1 -->|"DB_HOSTNAME=mariadb\n내부 ClusterIP"| db1
      PRI1 --> NAT1
    end

    subgraph VPC2["eksdemo2 VPC — 192.168.0.0/16"]
      direction TB
      ALB2[ALB\necr-ingress\ninternet-facing]
      NLB2[NLB\nmariadb-nlb :3306\ninternet-facing]

      subgraph PUB2["Public Subnets (192.168.x.x)"]
        NAT2[NAT Gateway]
      end

      subgraph EKS2["EKS eksdemo2 (NodeGroup: public)"]
        nginx2[kubeapp-ecr Pod\nNginx:1.0.0]
        be2[usermgmt-microservice\nSpring Boot :8095]
        db2[(MariaDB 11.4\nClusterIP: mariadb:3306)]
        ebs2[EBS Volume 4Gi\nStorageClass: ebs-sc]
        db2 --- ebs2
      end

      ALB2 -->|"/"| nginx2
      ALB2 -->|"/usermgmt"| be2
      be2 -->|"내부 ClusterIP"| db2
      NLB2 -->|TCP 3306| db2
    end

    subgraph PEERING["VPC Peering (제안됨 — 미구현)"]
      direction LR
      P1["eksdemo1 10.0.0.0/16"] <-.->|"pcx-xxxxx\nPrivate Route 양방향"| P2["eksdemo2 192.168.0.0/16"]
    end
  end

  User -->|HTTPS| ALB1
  User -->|HTTPS| ALB2
  DBeaver -->|TCP 3306| NLB2
  nginx1 -.->|image pull| ECR
  nginx2 -.->|image pull| ECR
```

---

## 3. 네트워크 구성

### eksdemo1 (10.0.0.0/16)
| 서브넷 | AZ | 유형 |
|---|---|---|
| 10.0.0.0/19 | ap-northeast-2a | Private |
| 10.0.32.0/19 | ap-northeast-2b | Private |
| 10.0.64.0/19 | ap-northeast-2a | Public |
| 10.0.96.0/19 | ap-northeast-2b | Public |

### eksdemo2 (192.168.0.0/16)
| 서브넷 | AZ | 유형 |
|---|---|---|
| 192.168.0.0/19 | ap-northeast-2a | Public |
| 192.168.32.0/19 | ap-northeast-2b | Public |
| 192.168.64.0/19 | ap-northeast-2a | Private |
| 192.168.96.0/19 | ap-northeast-2b | Private |

---

## 4. Kubernetes 워크로드 상세

### 공통 (eksdemo1 / eksdemo2 동일 구성)

| 리소스 | 이름 | 상세 |
|---|---|---|
| Deployment | `kubeapp-ecr` | ECR Nginx 이미지 (2 replicas) |
| Deployment | `mariadb` | MariaDB 11.4 (1 replica, Recreate) |
| Deployment | `usermgmt-microservice` | Spring Boot UserMgmt API |
| Service | `mariadb` | ClusterIP None (Headless) :3306 |
| Service | `kubeapp-ecr-nodeport-service` | NodePort :80 |
| Service | `usermgmt-restapp-service` | NodePort :8095 (nodePort 31231) |
| Ingress | `ecr-ingress-service` | ALB, ingressClassName: alb |
| PVC | `ebs-mariadb-pv-claim` | 4Gi, StorageClass: ebs-sc |
| ConfigMap | `usermanagement-dbcreation-script` | usermgmt DB 초기화 SQL |
| StorageClass | `ebs-sc` | ebs.csi.aws.com, WaitForFirstConsumer |

### eksdemo2 추가
| 리소스 | 이름 | 상세 |
|---|---|---|
| Service | `mariadb-nlb` | LoadBalancer (NLB, internet-facing) :3306 |

---

## 5. IAM / Add-on 구성

| 구성 요소 | eksdemo1 | eksdemo2 |
|---|---|---|
| OIDC Provider | ✅ | ✅ |
| EBS CSI Driver | ✅ (v1.55.0) | ✅ (v1.55.0) |
| AmazonEBSCSIDriverPolicy | NodeInstanceRole 연결 | NodeInstanceRole 연결 (2개) |
| AWS Load Balancer Controller | ✅ Helm + IRSA | ✅ Helm + IRSA |
| AWSLoadBalancerControllerIAMPolicy | IRSA 연결 | IRSA 연결 |
| ECR Pull 권한 | AmazonEC2ContainerRegistryPullOnly | AmazonEC2ContainerRegistryPullOnly + PowerUser |

---

## 6. ECR 리포지토리

| 항목 | 값 |
|---|---|
| URI | `086015456585.dkr.ecr.ap-northeast-2.amazonaws.com/aws-ecr-kubenginx` |
| 태그 | `1.0.0` |
| Tag Immutability | Enabled |
| Scan on Push | Enabled |

---

## 7. 접속 엔드포인트

| 용도 | URL |
|---|---|
| eksdemo1 Nginx | `http://ecr-ingress-eksdemo1-932013938.ap-northeast-2.elb.amazonaws.com/` |
| eksdemo1 UserMgmt API | `http://ecr-ingress-eksdemo1-932013938.ap-northeast-2.elb.amazonaws.com/usermgmt/health-status` |
| eksdemo2 Nginx | `http://ecr-ingress-1998677918.ap-northeast-2.elb.amazonaws.com/` |
| eksdemo2 UserMgmt API | `http://ecr-ingress-1998677918.ap-northeast-2.elb.amazonaws.com/usermgmt/health-status` |
| eksdemo2 MariaDB (DBeaver) | `k8s-default-mariadbn-a26d25ec7b-6138443a3b51e70c.elb.ap-northeast-2.amazonaws.com:3306` |

---

## 8. 크로스 VPC 연결 제안 (미구현)

VPC CIDR이 다르므로 VPC Peering을 통한 private 연결이 가능합니다.

```
eksdemo1 BE Pod (10.x.x.x)
  └─ VPC Peering (pcx-xxxxx)
       └─ eksdemo2 Internal NLB (192.168.x.x:3306)
            └─ MariaDB Pod
```

구현 단계:
1. VPC Peering 연결 생성 (eksdemo1 ↔ eksdemo2)
2. 양쪽 Route Table에 상대 CIDR 경로 추가
3. eksdemo2 보안 그룹: TCP 3306 from 10.0.0.0/16 허용
4. eksdemo2에 Internal NLB 생성 (mariadb 대상)
5. eksdemo1 `DB_HOSTNAME` = Internal NLB DNS 주소

---

## 9. 랩 폴더 구성

| 폴더 | 주제 |
|---|---|
| 01-EKS-Create-Cluster-using-eksctl | eksctl로 클러스터 생성 |
| 02-ECR-Elastic-Container-Registry-and-EKS | ECR + EKS 연동 |
| 04-EKS-Storage-with-EBS-ElasticBlockStore | EBS CSI + MariaDB |
| 05-Kubernetes-Important-Concepts | K8s 핵심 개념 |
| 06-EKS-Storage-with-RDS-Database | RDS 연동 |
| 07-ELB-Classic-and-Network-LoadBalancers | CLB / NLB |
| 08-ALB-Application-LoadBalancers | ALB Ingress |
| 09-EKS-Workloads-on-Fargate | Fargate |
| 11-NEW-DevOps-with-Github | GitHub CI/CD |
| 12-Microservices-Deployment-on-EKS | 마이크로서비스 |
| 13-Microservices-Distributed-Tracing-using-AWS-XRay-on-EKS | X-Ray |
| 14-Microservices-Canary-Deployments | 카나리 배포 |
| 15-EKS-HPA-Horizontal-Pod-Autoscaler | HPA |
| 16-EKS-VPA-Vertical-Pod-Autoscaler | VPA |
| 17-EKS-Autoscaling-Cluster-Autoscaler | Cluster Autoscaler |
| 18-EKS-Monitoring-using-Grafana | Grafana 모니터링 |
| 19-EKS-Docker-Advanced-WebRTC-Vue | WebRTC + Vue |
| 20-EKS-AI-Korean-Medi-RAG | AI RAG 서비스 |

---

> `stacksimplify` 계열 실습을 바탕으로 현재 워크스페이스 기준으로 재정리한 EKS 교육용 저장소입니다.

이 저장소는 Amazon EKS를 중심으로 클러스터 생성, 스토리지, 로드밸런싱, Fargate, DevOps, 마이크로서비스, 오토스케일링, 모니터링, 그리고 EKS 위에서 실제 앱을 서비스하는 실습까지 단계적으로 다룹니다.

## 현재 폴더 구성

| 번호 | 폴더 | 현재 실습 주제 |
| ---- | ---- | -------------- |
| 01 | [01-EKS-Create-Cluster-using-eksctl](/home/AWS-EKS-Class-Master/01-EKS-Create-Cluster-using-eksctl) | `eksctl`로 EKS 클러스터와 노드그룹 생성 |
| 02 | [02-ECR-Elastic-Container-Registry-and-EKS](/home/AWS-EKS-Class-Master/02-ECR-Elastic-Container-Registry-and-EKS) | Amazon ECR 연동 및 EKS에서 ECR 이미지 사용 |
| 04 | [04-EKS-Storage-with-EBS-ElasticBlockStore](/home/AWS-EKS-Class-Master/04-EKS-Storage-with-EBS-ElasticBlockStore) | EBS CSI Driver와 EKS 영구 스토리지 |
| 05 | [05-Kubernetes-Important-Concepts-for-Application-Deployments](/home/AWS-EKS-Class-Master/05-Kubernetes-Important-Concepts-for-Application-Deployments) | Pod, Deployment, Service, Secret, Init Container, Probe, Resource, Namespace 등 Kubernetes 핵심 개념 |
| 06 | [06-EKS-Storage-with-RDS-Database](/home/AWS-EKS-Class-Master/06-EKS-Storage-with-RDS-Database) | RDS와 연계한 애플리케이션 데이터 접근 |
| 07 | [07-ELB-Classic-and-Network-LoadBalancers](/home/AWS-EKS-Class-Master/07-ELB-Classic-and-Network-LoadBalancers) | CLB / NLB 기반 Service 노출 |
| 08 | [08-ALB-Application-LoadBalancers](/home/AWS-EKS-Class-Master/08-ALB-Application-LoadBalancers) | ALB Ingress, SSL, Redirect, ExternalDNS |
| 09 | [09-EKS-Workloads-on-Fargate](/home/AWS-EKS-Class-Master/09-EKS-Workloads-on-Fargate) | EKS Fargate 프로파일과 서버리스 워크로드 배포 |
| 11 | [11-NEW-DevOps-with-AWS-CdoeSeries](/home/AWS-EKS-Class-Master/11-NEW-DevOps-with-AWS-CdoeSeries) | AWS 개발자 도구 기반 DevOps 파이프라인 |
| 12 | [12-Microservices-Deployment-on-EKS](/home/AWS-EKS-Class-Master/12-Microservices-Deployment-on-EKS) | 마이크로서비스 배포, 서비스 디스커버리, AWS 아이콘 자산 |
| 13 | [13-Microservices-Distributed-Tracing-using-AWS-XRay-on-EKS](/home/AWS-EKS-Class-Master/13-Microservices-Distributed-Tracing-using-AWS-XRay-on-EKS) | AWS X-Ray 기반 분산 추적 |
| 14 | [14-Microservices-Canary-Deployments](/home/AWS-EKS-Class-Master/14-Microservices-Canary-Deployments) | NGINX 기반 stable / canary 배포 실습 |
| 15 | [15-EKS-HPA-Horizontal-Pod-Autoscaler](/home/AWS-EKS-Class-Master/15-EKS-HPA-Horizontal-Pod-Autoscaler) | HPA, Jupyter 세션 매니저, FE/BE/Redis, 사용자별 Notebook 실행 |
| 16 | [16-EKS-VPA-Vertical-Pod-Autoscaler](/home/AWS-EKS-Class-Master/16-EKS-VPA-Vertical-Pod-Autoscaler) | VPA 추천값, Pod 리소스 변경 관찰, 부하 테스트 |
| 17 | [17-EKS-Autoscaling-Cluster-Autoscaler](/home/AWS-EKS-Class-Master/17-EKS-Autoscaling-Cluster-Autoscaler) | Cluster Autoscaler와 노드 자동 확장 |
| 18 | [18-EKS-Monitoring-using-CloudWatch-Container-Insights](/home/AWS-EKS-Class-Master/18-EKS-Monitoring-using-CloudWatch-Container-Insights) | CloudWatch Container Insights, Log Insights, Prometheus, Grafana |
| 19 | [19-EKS-Docker-Advanced-WebRTC-Vue](/home/AWS-EKS-Class-Master/19-EKS-Docker-Advanced-WebRTC-Vue) | Docker-Advanced-WebRTC-Vue 앱을 EKS에서 CLB 기반으로 서비스 |
| 20 | [20-EKS-AI-Korean-Medi-RAG](/home/AWS-EKS-Class-Master/20-EKS-AI-Korean-Medi-RAG) | AI-Korean-Medi-RAG 앱을 EKS에서 CLB 기반으로 서비스 |

## 빠른 진입 링크

| 번호 | 대표 문서 | 핵심 포인트 |
| ---- | -------- | ----------- |
| 01 | [README.md](/home/AWS-EKS-Class-Master/01-EKS-Create-Cluster-using-eksctl/README.md) | `eksctl` 기반 EKS 클러스터 생성 시작점 |
| 02 | [README.md](/home/AWS-EKS-Class-Master/02-ECR-Elastic-Container-Registry-and-EKS/README.md) | ECR 리포지토리와 EKS 이미지 사용 |
| 04 | [README.md](/home/AWS-EKS-Class-Master/04-EKS-Storage-with-EBS-ElasticBlockStore/README.md) | EBS CSI Driver, StorageClass, PVC |
| 05 | [README.md](/home/AWS-EKS-Class-Master/05-Kubernetes-Important-Concepts-for-Application-Deployments/README.md) | Kubernetes 배포 핵심 개념 정리 |
| 06 | [README.md](/home/AWS-EKS-Class-Master/06-EKS-Storage-with-RDS-Database/README.md) | EKS와 RDS 연계 |
| 07 | [README.md](/home/AWS-EKS-Class-Master/07-ELB-Classic-and-Network-LoadBalancers/README.md) | CLB / NLB 서비스 노출 |
| 08 | [README.md](/home/AWS-EKS-Class-Master/08-ALB-Application-LoadBalancers/README.md) | ALB Ingress와 SSL, Redirect, DNS |
| 09 | [README.md](/home/AWS-EKS-Class-Master/09-EKS-Workloads-on-Fargate/README.md) | Fargate 워크로드 배포 |
| 11 | [README.md](/home/AWS-EKS-Class-Master/11-NEW-DevOps-with-AWS-CdoeSeries/README.md) | AWS Code 계열 DevOps 파이프라인 |
| 12 | [README.md](/home/AWS-EKS-Class-Master/12-Microservices-Deployment-on-EKS/README.md) | 마이크로서비스 배포 및 서비스 디스커버리 |
| 13 | [README.md](/home/AWS-EKS-Class-Master/13-Microservices-Distributed-Tracing-using-AWS-XRay-on-EKS/README.md) | X-Ray 분산 추적 |
| 14 | [README.md](/home/AWS-EKS-Class-Master/14-Microservices-Canary-Deployments/README.md) | stable / canary 트래픽 분산 |
| 15 | [README.md](/home/AWS-EKS-Class-Master/15-EKS-HPA-Horizontal-Pod-Autoscaler/README.md) | HPA와 Jupyter 세션 매니저 |
| 16 | [README.md](/home/AWS-EKS-Class-Master/16-EKS-VPA-Vertical-Pod-Autoscaler/README.md) | VPA 추천값과 리소스 변경 관찰 |
| 17 | [README.md](/home/AWS-EKS-Class-Master/17-EKS-Autoscaling-Cluster-Autoscaler/README.md) | Cluster Autoscaler 노드 확장 |
| 18 | [README.md](/home/AWS-EKS-Class-Master/18-EKS-Monitoring-using-CloudWatch-Container-Insights/README.md) | CloudWatch, Prometheus, Grafana |
| 19 | [README.md](/home/AWS-EKS-Class-Master/19-EKS-Docker-Advanced-WebRTC-Vue/README.md) | WebRTC 앱을 EKS + CLB로 서빙 |
| 20 | [README.md](/home/AWS-EKS-Class-Master/20-EKS-AI-Korean-Medi-RAG/README.md) | Medi-RAG 앱을 EKS + CLB로 서빙 |

## 참고할 점

- 현재 루트 기준으로 `03`, `10` 장 폴더는 없습니다.
- `08`, `11`, `19`, `20` 장은 기존 이름이나 주제에서 재편된 상태입니다.
- 19장과 20장은 단순 인프라 예제보다 “실제 GitHub 앱을 EKS에서 서비스하는 실습”에 초점을 맞춥니다.

## 저장소에서 다루는 큰 흐름

### 1. EKS 기초
- 클러스터 생성
- 노드그룹 운영
- `kubectl`, `eksctl` 사용

### 2. 스토리지와 데이터
- EBS CSI Driver
- PVC / PV / StorageClass
- RDS 연동

### 3. 트래픽 노출
- CLB / NLB
- ALB Ingress
- SSL / Redirect / ExternalDNS
- Fargate에서의 외부 노출

### 4. 애플리케이션 운영
- 마이크로서비스 배포
- X-Ray 분산 추적
- Canary 배포
- HPA / VPA / Cluster Autoscaler

### 5. 관측성과 운영 자동화
- CloudWatch Container Insights
- CloudWatch Log Insights / Alarm
- Prometheus / Grafana
- AWS DevOps 서비스 연계

### 6. 실제 앱 서빙 실습
- WebRTC 협업 앱
- 의료 RAG 앱

## 현재 기준 핵심 AWS / Kubernetes 주제

### AWS
- Amazon EKS
- Amazon ECR
- Amazon EBS
- Amazon RDS
- Classic Load Balancer / Network Load Balancer / Application Load Balancer
- AWS Fargate
- AWS X-Ray
- Amazon CloudWatch
- Route 53
- AWS Certificate Manager
- AWS Code 시리즈

### Kubernetes
- Namespace
- Pod / ReplicaSet / Deployment
- Service / Ingress
- Secret / ConfigMap
- Init Container
- Liveness / Readiness Probe
- Requests / Limits
- StorageClass / PV / PVC
- DaemonSet
- Canary Deployment
- HPA / VPA / Cluster Autoscaler

## 추천 학습 순서

1. `01`, `02`로 클러스터 생성과 ECR 사용 흐름 익히기
2. `04`, `05`, `06`으로 스토리지와 Kubernetes 기본기 학습
3. `07`, `08`, `09`로 외부 노출과 Fargate 학습
4. `12`, `13`, `14`로 마이크로서비스 운영 패턴 익히기
5. `15`, `16`, `17`, `18`로 오토스케일링과 모니터링 실습
6. `19`, `20`으로 실제 앱 서빙 실습 연결

## 이 저장소로 배우는 것

- EKS 클러스터를 직접 만들고 운영하는 방법
- Kubernetes 핵심 리소스를 AWS 환경과 결합하는 방법
- 스토리지, 로드밸런서, Ingress, Fargate를 실습으로 익히는 방법
- 마이크로서비스 운영, 오토스케일링, 모니터링 패턴
- CloudWatch / Prometheus / Grafana로 운영 가시성을 확보하는 방법
- 실제 애플리케이션을 EKS 위에 올려 서비스하는 방법

## 실습 전제

- AWS 계정이 필요합니다.
- 실습에 따라 ECR, ELB, EBS, CloudWatch 등 과금 리소스가 생성될 수 있습니다.
- 실습 종료 후 EKS 클러스터, 노드, LoadBalancer, PVC, ECR 이미지를 정리하는 습관이 중요합니다.

## 리소스 정리 기록

이 저장소 기준으로 `eksdemo1`, `eksdemo2` 실습을 진행한 뒤 실제로 수행한 정리 절차와 비용 관점 점검 결과를 기록합니다.

### 정리 대상과 수행 내용

| 구분 | 수행 내용 | 비고 |
| ---- | -------- | ---- |
| `EKS Cluster` | `eksctl delete cluster --name eksdemo1 --region ap-northeast-2 --wait` 수행 | `eksdemo1` 클러스터, 노드그룹, 제어 플레인 삭제 |
| `CloudFormation` | `eksctl`가 관리하던 `eksdemo1` 관련 스택 삭제 확인 | `eksctl-eksdemo1-*` 스택 제거 |
| `OIDC / IAM SA` | `aws-load-balancer-controller` service account 스택과 OIDC provider 삭제 확인 | `eksdemo1` 전용 OIDC provider 제거 |
| `Load Balancer` | `eksdemo1` 관련 ALB / NLB 제거 확인 | 활성 ELB 리소스 없음 |
| `ECR` | `jupyter-manager`, `jupyter-minimal-notebook` 리포지토리 삭제 | `eksdemo2`에서 사용 중인 이미지 제외 |
| `EBS` | unattached `available` EBS 볼륨 6개 삭제 | PV / PVC가 없는 것 확인 후 제거 |
| `VPC` | `eksdemo1` VPC와 관련 subnet / NAT / ENI 삭제 확인 | 콘솔의 `Deleted` NAT 표시는 삭제 이력 |
| `kubeconfig` | stale `eksdemo1` context / cluster / user 삭제 | 로컬 `~/.kube/config` 정리 |

### 실제 정리 순서

1. 현재 `kubectl` context와 EKS 클러스터 목록 확인
2. `eksdemo1` 관련 CloudFormation 스택과 OIDC provider 확인
3. `eksctl delete cluster`로 클러스터 및 관리 스택 삭제
4. `eksdemo1` 전용 OIDC / IAM service account / Load Balancer 정리 여부 확인
5. `jupyter-*` ECR 리포지토리 삭제
6. unattached `available` EBS 볼륨 삭제
7. `VPC`, `NAT`, `ENI`, `Security Group`, `Target Group`, `EIP` 잔여 여부 재점검
8. `kubectl config`에서 stale context 제거

### 비용 관점 점검 체크리스트

실습 종료 후 아래 항목을 우선 확인하면 과금 잔여물을 빠르게 찾을 수 있습니다.

| 서비스 | 우선 확인 항목 | 과금 포인트 |
| ------ | ------------- | ---------- |
| `EC2` | `running`, `stopped` 인스턴스 | 인스턴스 시간 과금 |
| `ELB / ALB / NLB` | 활성 Load Balancer, Target Group | 시간 + 처리량 과금 |
| `EBS` | `available` 볼륨, 스냅샷 | 저장 공간 과금 |
| `ECR` | 리포지토리, 이미지 레이어 | 저장 공간 과금 |
| `CloudFormation` | `CREATE_COMPLETE`, `DELETE_FAILED` 스택 | 스택 자체보다 스택이 만든 자원 과금 |
| `VPC` | NAT Gateway, EIP, ENI | NAT 시간/데이터, 미사용 EIP 과금 |

### 최종 점검 결과

`ap-northeast-2` 리전 기준 최종 확인 결과는 아래와 같습니다.

- `EC2`: `running` / `stopped` 인스턴스 없음
- `ELB / ALB / NLB`: 없음
- `EBS Volume`: 없음
- `EBS Snapshot`: 없음
- `ECR Repository`: 없음
- `CloudFormation Active Stack`: 없음
- `EIP`: 없음
- `eksdemo1` / `eksdemo2` VPC: 없음

### 주의 사항

- AWS 콘솔에 `Deleted` 상태 NAT Gateway가 잠시 보일 수 있습니다.
- 이 항목은 실제 과금 자원이 아니라 삭제 이력으로 남아 있는 메타데이터일 수 있습니다.
- `ECR`, `EBS`, `NLB`는 다른 클러스터나 다른 실습에서 공유할 수 있으므로, 삭제 전에 실제 참조 여부를 먼저 확인해야 합니다.
- 비용 점검은 반드시 리전별로 확인해야 하며, 다른 리전에 자원이 남아 있으면 별도 과금될 수 있습니다.

## 대상 학습자

- AWS에서 Kubernetes를 운영하려는 아키텍트, 개발자, 시스템 관리자
- EKS를 중심으로 실습형으로 배우고 싶은 초급~중급 학습자
- DevOps, 마이크로서비스, 오토스케일링, 모니터링을 함께 익히고 싶은 분

## 부록

### 워커 노드 삭제 시 Pod 이전 여부와 시간

EKS에서 워커 노드를 정상 절차로 제거하면, 대부분의 Deployment / ReplicaSet 기반 Pod는 다른 노드로 재스케줄됩니다. 다만 StatefulSet, EBS 볼륨, PDB, 이미지 Pull, Probe, `terminationGracePeriodSeconds` 같은 조건에 따라 수십 초에서 수분까지 차이가 날 수 있습니다.

권장 절차:

```bash
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

이후 Managed Node Group 또는 ASG desired 값을 줄이는 방식이 일반적입니다.

이벤트 확인:

```bash
kubectl get events -A --sort-by=.lastTimestamp | tail -n 50
```

### 삭제 전 termination protection 해제 예시

```bash
aws --profile "default" --region "ap-northeast-2" cloudformation update-termination-protection \
  --stack-name eksdemo1-cluster \
  --no-enable-termination-protection
```

### 3D 아키텍처 참고

https://app.cloudcraft.co/view/d49525d1-c004-4604-a228-765fae1ae18a?key=736e0286-1c5f-444a-9ce7-282027410eff
