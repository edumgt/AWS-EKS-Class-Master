## AWS EKS

> stacksimplify 의 repo 를 응용한 EKS 교육용 repo 입니다.

| 번호 | AWS 서비스 이름 |
| ---- | ---------------- |
| 1.   | eksctl CLI를 사용해 AWS EKS 클러스터 생성 |
| 4.   | AWS EBS CSI 드라이버를 사용한 EKS 스토리지 |
| 5.   | 애플리케이션 배포를 위한 Kubernetes 핵심 개념 |
| 5.1  | Kubernetes - 시크릿 |
| 5.2  | Kubernetes - 초기화 컨테이너 |
| 5.3  | Kubernetes - Liveness & Readiness 프로브 |
| 5.4  | Kubernetes - 요청 & 제한 |
| 5.5  | Kubernetes - 네임스페이스, 리밋 레인지, 리소스 쿼터 |
| 6.   | AWS RDS MySQL 데이터베이스를 사용하는 EKS 스토리지 |
| 7.   | CLB 및 NLB를 사용한 로드 밸런싱 |
| 7.1  | CLB를 사용한 로드 밸런싱 - AWS Classic Load Balancer |
| 7.2  | NLB를 사용한 로드 밸런싱 - AWS Network Load Balancer |
| 8.   | ALB를 사용한 로드 밸런싱 - AWS Application Load Balancer |
| 8.1  | ALB Ingress Controller - 설치 |
| 8.2  | ALB Ingress - 기본 |
| 8.3  | ALB Ingress - 컨텍스트 경로 기반 라우팅 |
| 8.4  | ALB Ingress - SSL |
| 8.5  | ALB Ingress - HTTP에서 HTTPS로 SSL 리다이렉트 |
| 8.6  | ALB Ingress - External DNS |
| 9.   | AWS Fargate 서버리스에 Kubernetes 워크로드 배포 |
| 9.1  | AWS Fargate 프로파일 - 기본 |
| 9.2  | AWS Fargate 프로파일 - YAML을 사용한 고급 |
| 10.  | AWS ECR에 컨테이너를 빌드/푸시하고 EKS에서 사용 |
| 11.  | AWS Developer Tools(CodeCommit, CodeBuild, CodePipeline)로 DevOps |
| 12.  | EKS에서 마이크로서비스 배포 - 서비스 디스커버리 |
| 13.  | AWS X-Ray를 사용한 마이크로서비스 분산 추적 |
| 14.  | 마이크로서비스 카나리 배포 |
| 15.  | EKS HPA - 수평 Pod 오토스케일러 |
| 16.  | EKS VPA - 수직 Pod 오토스케일러 |
| 17.  | EKS CA - 클러스터 오토스케일러 |
| 18.  | CloudWatch Agent & Fluentd를 사용한 EKS 모니터링 - Container Insights |


## 다루는 AWS 서비스

| 번호 | AWS 서비스 이름 |
| ---- | ---------------- |
| 1.   | AWS EKS - Elastic Kubernetes Service  |
| 2.   | AWS EBS - Elastic Block Store  |
| 3.   | AWS RDS - Relational Database Service MySQL  |
| 4.   | AWS CLB - Classic Load Balancer  |
| 5.   | AWS NLB - Network Load Balancer  |
| 6.   | AWS ALB - Application Load Balancer  |
| 7.   | AWS Fargate - Serverless  |
| 8.   | AWS ECR - Elastic Container Registry  |
| 9.   | AWS 개발자 도구 - CodeCommit  |
| 10.  | AWS 개발자 도구 - CodeBuild  |
| 11.  | AWS 개발자 도구 - CodePipeline  |
| 12.  | AWS X-Ray  |
| 13.  | AWS CloudWatch - Container Insights  |
| 14.  | AWS CloudWatch - 로그 그룹 & Log Insights  |
| 15.  | AWS CloudWatch - 알람  |
| 16.  | AWS Route53  |
| 17.  | AWS Certificate Manager  |
| 18.  | EKS CLI - eksctl  |


## 다루는 Kubernetes 개념

| 번호 | Kubernetes 개념 이름 |
| ---- | ------------------- |
| 1.   | Kubernetes 아키텍처  |
| 2.   | 파드(Pods)  |
| 3.   | 레플리카셋(ReplicaSets)  |
| 4.   | 디플로이먼트(Deployments)  |
| 5.   | 서비스 - 노드 포트 서비스  |
| 6.   | 서비스 - 클러스터 IP 서비스  |
| 7.   | 서비스 - External Name 서비스  |
| 8.   | 서비스 - Ingress 서비스  |
| 9.   | 서비스 - Ingress SSL & SSL 리다이렉트  |
| 10.  | 서비스 - Ingress & External DNS  |
| 11.  | 명령형 - kubectl 사용  |
| 12.  | 선언형 - YAML로 선언형 작성  |
| 13.  | 시크릿(Secrets) |
| 14.  | 초기화 컨테이너(Init Containers) |
| 15.  | Liveness & Readiness 프로브 |
| 16.  | 요청 & 제한 |
| 17.  | 네임스페이스 - 명령형 |
| 18.  | 네임스페이스 - 리밋 레인지 |
| 19.  | 네임스페이스 - 리소스 쿼터 |
| 20.  | 스토리지 클래스 |
| 21.  | 퍼시스턴트 볼륨 |
| 22.  | 퍼시스턴트 볼륨 클레임 |
| 23.  | 서비스 - 로드 밸런서 |
| 24.  | 애노테이션 |
| 25.  | 카나리 배포 |
| 26.  | HPA - 수평 Pod 오토스케일러 |
| 27.  | VPA - 수직 Pod 오토스케일러 |
| 28.  | CA - 클러스터 오토스케일러 |
| 29.  | 데몬셋(DaemonSets) |
| 30.  | 데몬셋 - 로그용 Fluentd |
| 31.  | ConfigMap |

## Docker Hub의 Docker 이미지 목록

| 애플리케이션 이름  | Docker 이미지 이름 |
| ----------------- | ----------------- |
| Simple Nginx V1  | stacksimplify/kubenginx:1.0.0  |
| Spring Boot Hello World API  | stacksimplify/kube-helloworld:1.0.0  |
| Simple Nginx V2  | stacksimplify/kubenginx:2.0.0  |
| Simple Nginx V3  | stacksimplify/kubenginx:3.0.0  |
| Simple Nginx V4  | stacksimplify/kubenginx:4.0.0  |
| Backend Application  | stacksimplify/kube-helloworld:1.0.0  |
| Frontend Application  | stacksimplify/kube-frontend-nginx:1.0.0  |
| Kube Nginx App1  | stacksimplify/kube-nginxapp1:1.0.0  |
| Kube Nginx App2  | stacksimplify/kube-nginxapp2:1.0.0  |
| Kube Nginx App2  | stacksimplify/kube-nginxapp2:1.0.0  |
| User Management Microservice with MySQLDB  | stacksimplify/kube-usermanagement-microservice:1.0.0  |
| User Management Microservice with H2 DB  | stacksimplify/kube-usermanagement-microservice:2.0.0-H2DB  |
| User Management Microservice with MySQL DB and AWS X-Ray  | stacksimplify/kube-usermanagement-microservice:3.0.0-AWS-XRay-MySQLDB  |
| User Management Microservice with H2 DB and AWS X-Ray  | stacksimplify/kube-usermanagement-microservice:4.0.0-AWS-XRay-H2DB  |
| Notification Microservice V1  | stacksimplify/kube-notifications-microservice:1.0.0  |
| Notification Microservice V2  | stacksimplify/kube-notifications-microservice:2.0.0  |
| Notification Microservice V1 with AWS X-Ray  | stacksimplify/kube-notifications-microservice:3.0.0-AWS-XRay  |
| Notification Microservice V2 with AWS X-Ray  | stacksimplify/kube-notifications-microservice:4.0.0-AWS-XRay  |


## AWS ECR에서 빌드하는 Docker 이미지 목록

| 애플리케이션 이름  | Docker 이미지 이름 |
| ----------------- | ----------------- |
| AWS Elastic Container Registry  | YOUR-AWS-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/aws-ecr-kubenginx:DATETIME-REPOID  |
| DevOps 유스케이스  | YOUR-AWS-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/eks-devops-nginx:DATETIME-REPOID  |


## 샘플 애플리케이션
- 사용자 관리 마이크로서비스
- 알림 마이크로서비스
- Nginx 애플리케이션

## 이 과정에서 무엇을 배우나요?
- 실시간 템플릿 작성 섹션을 통해 자신 있게 Kubernetes 매니페스트를 작성할 수 있습니다.
- 30개 이상의 Kubernetes 개념을 배우고 EKS와 조합해 18개의 AWS 서비스를 사용합니다.
- 명령형과 선언형 방식 모두에서 Kubernetes 기초를 학습합니다.
- 스토리지 클래스, 퍼시스턴트 볼륨 클레임(PVC), MySQL, EBS CSI Driver 같은 스토리지 개념의 k8s 매니페스트를 작성 및 배포합니다.
- k8s External Name 서비스를 사용해 기본 EBS 스토리지에서 RDS 데이터베이스로 전환하는 방법을 배웁니다.
- Classic 및 Network 로드 밸런서용 k8s 매니페스트를 작성하고 배포합니다.
- 컨텍스트 경로 기반 라우팅, SSL, SSL 리다이렉트, External DNS 같은 기능을 활성화하는 Ingress k8s 매니페스트를 작성합니다.
- 고급 Fargate 프로파일용 k8s 매니페스트를 작성하고 EC2와 Fargate 서버리스를 혼합한 워크로드 배포를 진행합니다.
- EKS와 함께 ECR(Elastic Container Registry)을 사용하는 방법을 배웁니다.
- CodeCommit, CodeBuild, CodePipeline 같은 AWS Code 서비스로 DevOps 개념을 구현합니다.
- 서비스 디스커버리, X-Ray를 통한 분산 추적, 카나리 배포 같은 마이크로서비스 핵심 개념을 구현합니다.
- HPA, VPA, 클러스터 오토스케일러 같은 오토스케일링 기능을 활성화하는 방법을 배웁니다.
- CloudWatch Container Insights를 사용해 EKS 클러스터 및 워크로드의 모니터링과 로깅을 활성화합니다.
- Docker Hub에서 이미지 다운로드, 로컬에서 실행, 로컬 빌드/테스트 후 Docker Hub로 푸시 등 실습을 통해 Docker 기초를 익힙니다.
- Docker 기초부터 시작해 Kubernetes로 단계적으로 이동합니다.
- 과정 전반에 걸쳐 다양한 kubectl 명령을 숙달합니다.

## 과정 수강 요건이나 사전 지식이 있나요?
- 실습을 따라 하려면 AWS 계정이 필요합니다.
- 이 과정을 시작하기 위해 기본 Docker나 Kubernetes 지식이 반드시 필요한 것은 아닙니다.


## 대상 학습자
- Kubernetes에서 애플리케이션을 실행하기 위해 Elastic Kubernetes Service(EKS)를 마스터하려는 AWS 아키텍트, 시스템 관리자, 개발자
- AWS EKS를 사용한 클라우드 Kubernetes 학습에 관심 있는 초보자
- Kubernetes에서 DevOps와 마이크로서비스 배포를 배우고 싶은 초보자


---
# EKS에서 워커 노드 삭제 시 Pod 이전 여부와 시간 소요

EKS에서 **워커 노드(노드 인스턴스)** 를 “정상 절차로” 제거하면, 그 노드에 있던 **대부분의 Pod는 다른 노드로 재스케줄(이전) 됩니다.**  
다만 **어떻게 삭제하느냐**(drain 했는지, 노드그룹/ASG에서 스케일다운인지, 그냥 인스턴스 강제 종료인지)에 따라 결과와 시간이 크게 달라집니다.

---

## 1) 워커 노드 삭제 시 Pod “이전” 되나?

### ✅ 일반적으로 “이전됨”(재생성/재배치)
- **Deployment / ReplicaSet / Job / CronJob**: 노드에서 빠지면 다른 노드에 **새로 생성**됨(=재스케줄).
- 노드가 **cordon + drain** 되면 kube-scheduler가 다른 노드로 배치.

### ⚠️ 예외/주의 케이스
- **DaemonSet Pod**: drain 시 기본적으로 “무시” 대상이라(옵션에 따라) *그 노드에만 있던 DaemonSet Pod는* 노드가 사라지면 같이 사라지고, **다른 노드에는 원래부터 DaemonSet이 떠있어야 정상**입니다(‘이전’ 개념이 아님).
- **StatefulSet**: Pod는 다른 노드로 뜰 수 있지만,
  - PV가 **EBS 같은 단일 AZ 볼륨**이면 **같은 AZ의 다른 노드**로만 옮겨질 가능성이 큼
  - 볼륨 attach/detach 때문에 시간이 더 걸릴 수 있음
- **PodDisruptionBudget(PDB)**: 동시에 내릴 수 있는 Pod 수를 제한해서 drain이 **멈추거나 오래 걸릴 수 있음**
- **노드에 남는/막히는 Pod**: `emptyDir` 데이터가 있는 Pod, local PV 등은 정책/옵션에 따라 삭제가 막히거나 데이터 유실 이슈가 생길 수 있음

---

## 2) 시간 소요는?

정확한 “고정 시간”은 없고, 아래 요소의 합으로 결정됩니다.

### (A) 종료/퇴거(Evict) 시간
- `terminationGracePeriodSeconds` (기본 30s)  
- 앱이 SIGTERM 받고 **정리 종료**를 얼마나 빨리 하는지
- **PDB** 때문에 한 번에 못 빼면 대기 발생

### (B) 재스케줄/기동 시간
- 스케줄링 자체는 보통 빠르지만,
- **이미지 pull**(캐시 없으면 오래 걸림)
- **볼륨 attach/detach(EBS)**  
- **ReadinessProbe** 통과까지의 시간(앱 웜업 포함)

> 체감상은 보통 **수십 초 ~ 수분** 범위에서 많이 끝나지만,  
> PDB/볼륨/이미지 pull/웜업이 크면 **더 길어질 수 있습니다**(특히 Stateful 워크로드).

---

## 3) “어떻게 삭제하느냐”가 제일 중요

### ✅ 권장: cordon + drain 후 노드 제거(또는 노드그룹 스케일다운)
```bash
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

그 다음에
- Managed Node Group이면: **노드그룹 desired 감소**(eksctl scale nodegroup / 콘솔 / ASG)
- 또는 eksctl로 nodegroup 삭제

### ❌ 비권장: 인스턴스 강제 terminate / node 오브젝트만 delete
- 갑자기 노드가 죽으면 Pod가 **정상 종료 절차를 못 밟고**,  
  일부는 **Terminating/Unknown** 상태로 오래 남거나,
- 스토리지 detach가 꼬이면 복구가 늦어질 수 있습니다.

---

## 4) 체크 포인트(이전/시간 확인)

### drain 진행 확인
```bash
kubectl get pods -A -o wide | grep <node-name>
kubectl describe node <node-name> | egrep -i "unschedulable|taint|condition"
```

### 이벤트로 막히는 원인 확인(PDB, 볼륨 등)
```bash
kubectl get events -A --sort-by=.lastTimestamp | tail -n 50
```

---

### 삭제 전 필요 작업
```
ubuntu@DESKTOP-8FSFFJK:~/Eks-Class$ aws --profile "default" --region "ap-northeast-2" cloudformation update-termination-protection   --stack-name eksctl-eksdem
o1-cluster   --no-enable-termination-protection
{
    "StackId": "arn:aws:cloudformation:ap-northeast-2:086015456585:stack/eksctl-eksdemo1-cluster/bc064830-0009-11f1-a846-020a1fbd0057"
}
```


---
### 3D 포맷의 아키텍쳐 구성도
https://app.cloudcraft.co/view/d49525d1-c004-4604-a228-765fae1ae18a?key=736e0286-1c5f-444a-9ce7-282027410eff

![](./cloudcraft%20ap-northeast-2.png)