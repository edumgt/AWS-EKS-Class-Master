# 20. Apache Airflow on EKS (Pod 방식)

## Step-01: 소개

### Apache Airflow 란?
- 워크플로우(DAG: Directed Acyclic Graph)를 코드로 정의·스케줄·모니터링하는 오픈소스 플랫폼
- ETL 파이프라인, ML 파이프라인, 배치 작업 오케스트레이션에 널리 사용
- Python 기반 DAG 작성, 풍부한 Operator/Provider 생태계

### 이 챕터에서 구성하는 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│ EKS Cluster (ap-northeast-2)  — Namespace: airflow          │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │  Airflow     │   │  Airflow     │   │  Airflow       │  │
│  │  Webserver   │   │  Scheduler   │   │  Triggerer     │  │
│  │  (Pod)       │   │  (Pod)       │   │  (Pod)         │  │
│  └──────┬───────┘   └──────┬───────┘   └────────────────┘  │
│         │                  │                                 │
│         │      ┌───────────┴──────────────────────────┐     │
│         │      │  KubernetesExecutor                  │     │
│         │      │  → 태스크마다 Worker Pod 동적 생성   │     │
│         │      └──────────────────────────────────────┘     │
│         │                                                    │
│  ┌──────┴──────────────────────────┐                        │
│  │  MariaDB (StatefulSet Pod)      │  ← EBS gp3 (20Gi)     │
│  │  Airflow 메타데이터 DB          │                        │
│  └─────────────────────────────────┘                        │
│                                                             │
│  ┌─────────────────────────────────┐                        │
│  │  EBS PVC (로그 저장소, 10Gi)   │                        │
│  └─────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
         ↑ ALB Ingress (HTTPS:443 → airflow-webserver:8080)
```

### 사용 컴포넌트

| 컴포넌트 | 설명 |
|---------|------|
| Apache Airflow 2.9.x | 워크플로우 플랫폼 (Helm Chart 설치) |
| KubernetesExecutor | 태스크를 EKS Pod 로 실행 |
| MariaDB 11.4 | Airflow 메타데이터 DB (StatefulSet Pod) |
| EBS gp3 | MariaDB 데이터 + Airflow 로그 영구 저장 |
| GitSync | DAG 파일을 git repo 에서 자동 동기화 |
| ALB Ingress | Airflow Web UI 외부 노출 |

---

## Step-02: 사전 조건 확인

```bash
# EKS 클러스터 및 노드 확인
kubectl get nodes -o wide

# EBS CSI Driver 확인 (Chapter 04 참고)
kubectl get pods -n kube-system | grep ebs-csi

# AWS Load Balancer Controller 확인 (Chapter 08 참고)
kubectl get pods -n kube-system | grep aws-load-balancer-controller

# Helm 설치 확인
helm version
```

---

## Step-03: MariaDB Pod 설치 (Airflow 메타데이터 DB)

### Step-03-01: Namespace 및 StorageClass 생성
```bash
# Namespace 생성
kubectl apply -f kube-manifests/01-namespace.yaml

# EBS StorageClass 생성
kubectl apply -f kube-manifests/02-storage-class.yaml

# 확인
kubectl get namespace airflow
kubectl get storageclass airflow-ebs-sc
```

### Step-03-02: MariaDB Secret 적용
```bash
# 운영 환경에서는 비밀번호를 반드시 변경하세요!
kubectl apply -f kube-manifests/03-mariadb-secret.yaml

# 확인
kubectl get secret mariadb-secret -n airflow
```

### Step-03-03: MariaDB StatefulSet 배포
```bash
kubectl apply -f kube-manifests/04-mariadb-statefulset.yaml
kubectl apply -f kube-manifests/05-mariadb-service.yaml

# Pod 및 PVC 상태 확인 (Running 상태 대기)
kubectl get pods -n airflow -w
kubectl get pvc -n airflow
kubectl get pv
```

### Step-03-04: MariaDB 연결 테스트
```bash
# MariaDB Pod 이름 확인
kubectl get pods -n airflow -l app=mariadb

# MariaDB 접속 테스트
kubectl exec -it mariadb-0 -n airflow -- \
  mysql -u airflow -p'airflow123!' airflow_meta -e "SELECT VERSION();"
```

---

### 🔍 기술 심화: Headless Service 와 StatefulSet DNS

#### Headless Service 란?

일반 `ClusterIP` 서비스는 kube-proxy 가 가상 IP(VIP)를 하나 할당하고,  
그 VIP 로 들어오는 트래픽을 뒤쪽 Pod 들에 **로드밸런싱**합니다.

**Headless Service** (`clusterIP: None`) 는 VIP 를 전혀 할당하지 않습니다.  
대신 CoreDNS 가 서비스 이름 쿼리에 대해 **Pod IP 를 직접 반환**합니다.

```
일반 ClusterIP 서비스 DNS 흐름
─────────────────────────────────────────────────────────────
클라이언트  →  mariadb.airflow.svc.cluster.local
              ↓ DNS 쿼리 (CoreDNS)
              ↓ 단일 가상 IP (예: 10.100.45.23) 반환  ← VIP
              ↓ kube-proxy 에 의해 실제 Pod IP 로 DNAT

Headless Service DNS 흐름
─────────────────────────────────────────────────────────────
클라이언트  →  mariadb.airflow.svc.cluster.local
              ↓ DNS 쿼리 (CoreDNS)
              ↓ 실제 Pod IP 목록 직접 반환 (A 레코드 다수)
              ↓ 클라이언트가 직접 Pod IP 에 연결
```

#### StatefulSet + Headless Service = 안정적 Pod DNS

StatefulSet 의 `spec.serviceName` 이 Headless Service 이름과 연결되면,  
각 Pod 는 아래 형식의 **고정 DNS 이름**을 부여받습니다.

```
<pod-name>.<headless-service-name>.<namespace>.svc.cluster.local

예시:
  mariadb-0.mariadb.airflow.svc.cluster.local  ← mariadb-0 Pod 의 고정 DNS
  mariadb-1.mariadb.airflow.svc.cluster.local  ← replicas 늘릴 경우
```

Pod 가 재시작되거나 다른 노드로 이동해도 **DNS 이름은 변하지 않습니다.**  
IP 는 바뀌지만 CoreDNS 가 새 IP 로 자동 업데이트합니다.

#### 일반 Deployment 에서는 왜 이것이 불가능한가?

| 항목 | Deployment + ClusterIP | StatefulSet + Headless |
|------|------------------------|------------------------|
| Pod 이름 | 랜덤 해시 (nginx-7d4f9c-xk2p8) | 순번 고정 (mariadb-0) |
| 개별 Pod DNS | ❌ 없음 | ✅ pod-name.svc.ns.svc.cluster.local |
| Pod 재시작 후 DNS | 변경됨 | 동일 이름 유지 |
| 영구 볼륨 재연결 | ❌ 보장 안 됨 | ✅ 같은 PVC 재마운트 보장 |
| DB 등 Stateful 워크로드 | 부적합 | 적합 |

#### Airflow 가 Headless DNS 를 사용하는 이유

```yaml
# helm-values/airflow-values.yaml
data:
  metadataConnection:
    host: mariadb.airflow.svc.cluster.local  # ← Headless Service 이름
```

- `mariadb.airflow.svc.cluster.local` 은 Headless Service 이름으로 쿼리하면  
  현재 Running 상태인 `mariadb-0` 의 Pod IP 를 직접 반환합니다.
- MariaDB 는 단일 인스턴스 DB 이므로 로드밸런싱이 필요 없고,  
  특정 Pod(mariadb-0)에 **직접 연결**하는 것이 올바른 동작입니다.
- Pod IP 가 변경되어도 DNS 가 자동으로 새 IP 로 갱신되므로  
  Airflow 코드 변경 없이 재연결이 가능합니다.

#### DNS 동작 실습 확인

```bash
# CoreDNS 가 Headless Service 에 대해 반환하는 레코드 확인
# (임시 nslookup Pod 실행)
kubectl run -it --rm dns-test --image=busybox:1.36 --restart=Never \
  --namespace airflow -- sh -c "
    echo '=== Headless Service (Pod IP 직접 반환) ==='
    nslookup mariadb.airflow.svc.cluster.local

    echo '=== StatefulSet Pod 개별 DNS ==='
    nslookup mariadb-0.mariadb.airflow.svc.cluster.local
  "

# 예상 출력:
# === Headless Service (Pod IP 직접 반환) ===
# Server:    10.96.0.10
# Address 1: 10.96.0.10 kube-dns.kube-system.svc.cluster.local
# Name:      mariadb.airflow.svc.cluster.local
# Address 1: 192.168.12.45   ← mariadb-0 의 실제 Pod IP
#
# === StatefulSet Pod 개별 DNS ===
# Name:      mariadb-0.mariadb.airflow.svc.cluster.local
# Address 1: 192.168.12.45   ← 동일한 Pod IP

# SRV 레코드도 자동 생성됨 (포트 정보 포함)
kubectl run -it --rm dns-test --image=busybox:1.36 --restart=Never \
  --namespace airflow -- nslookup -type=SRV \
  _mysql._tcp.mariadb.airflow.svc.cluster.local
```

#### DNS 쿼리 경로 (내부 구조)

```
Airflow Pod (airflow namespace)
  │
  │  getaddrinfo("mariadb.airflow.svc.cluster.local")
  ↓
/etc/resolv.conf (Pod 내부)
  nameserver 10.96.0.10        ← kube-dns ClusterIP (CoreDNS)
  search airflow.svc.cluster.local svc.cluster.local cluster.local
  │
  ↓  UDP 53 쿼리
CoreDNS Pod (kube-system namespace)
  │  etcd / kube-apiserver 에서 Endpoints 조회
  │  mariadb Service → clusterIP: None → Endpoints 에서 Pod IP 열람
  ↓
응답: A 레코드 → 192.168.12.45 (mariadb-0 Pod IP)
  │
  ↓  TCP 3306 직접 연결
MariaDB Pod (mariadb-0)
```

---

## Step-04: Fernet Key 및 Webserver Secret Key 생성

Airflow 는 DB에 저장하는 민감 정보를 Fernet 키로 암호화합니다.
**설치 전에 반드시 고유한 키를 생성하여 `airflow-values.yaml` 에 입력하세요.**

```bash
# Fernet Key 생성 (Python 필요)
python3 -c "
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print('fernetKey:', key)
"

# Webserver Secret Key 생성
python3 -c "
import secrets
print('webserverSecretKey:', secrets.token_hex(32))
"
```

생성된 값을 `helm-values/airflow-values.yaml` 에서 교체합니다:
```yaml
fernetKey: "생성된-fernet-key-값"
webserverSecretKey: "생성된-webserver-secret-key-값"
```

---

## Step-05: Airflow Helm Chart 설치

### Step-05-01: Helm 레포지토리 추가
```bash
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# 사용 가능한 Airflow 차트 버전 확인
helm search repo apache-airflow/airflow --versions | head -10
```

### Step-05-02: Airflow 설치 (MariaDB 연동, KubernetesExecutor)
```bash
helm upgrade --install airflow apache-airflow/airflow \
  --namespace airflow \
  --values helm-values/airflow-values.yaml \
  --timeout 10m0s \
  --wait

# 설치 상태 확인
helm list -n airflow
kubectl get pods -n airflow
```

### Step-05-03: 설치 결과 확인
```bash
# 모든 Airflow Pod 확인
kubectl get pods -n airflow -o wide

# 예상 Pod 목록:
# airflow-scheduler-xxxx       — DAG 스케줄링
# airflow-webserver-xxxx       — Web UI
# airflow-triggerer-xxxx       — 비동기 Trigger
# mariadb-0                    — 메타데이터 DB

# 서비스 확인
kubectl get svc -n airflow

# PVC/PV 확인 (로그 저장소)
kubectl get pvc -n airflow
```

### Step-05-04: Webserver 초기화 로그 확인
```bash
# Webserver 로그 확인 (DB 마이그레이션 완료 확인)
kubectl logs -n airflow \
  $(kubectl get pods -n airflow -l component=webserver -o jsonpath='{.items[0].metadata.name}') \
  --tail=50

# Scheduler 로그 확인
kubectl logs -n airflow \
  $(kubectl get pods -n airflow -l component=scheduler -o jsonpath='{.items[0].metadata.name}') \
  --tail=50
```

---

## Step-06: ALB Ingress 설정 (Web UI 외부 노출)

### Step-06-01: Ingress 적용
```bash
# SSL 을 사용하는 경우 06-airflow-ingress.yaml 에서 certificate-arn 주석 해제 후 ARN 입력
kubectl apply -f kube-manifests/06-airflow-ingress.yaml

# Ingress 상태 및 ALB DNS 확인 (ADDRESS 컬럼에 ALB DNS가 나타날 때까지 대기)
kubectl get ingress -n airflow -w
```

### Step-06-02: 브라우저 접속
```bash
# ALB DNS 주소 확인
ALB_DNS=$(kubectl get ingress airflow-ingress -n airflow \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Airflow URL: http://$ALB_DNS"

# 기본 로그인 정보 (airflow-values.yaml 의 defaultUser 설정값)
# ID: admin
# PW: Admin1234!
```

> **⚠️ 운영 환경 주의:** `defaultUser.password` 는 반드시 강력한 비밀번호로 변경하고,  
> ACM SSL 인증서를 적용하여 HTTPS 로만 접근하도록 설정하세요.

---

## Step-07: DAG 배포 (GitSync 방식)

### Step-07-01: DAG 저장소 준비
```
your-dags-repo/
└── dags/
    ├── sample_etl_dag.py      ← 이 챕터의 예제 DAG
    └── (추가 DAG 파일들)
```

```bash
# 샘플 DAG 파일 위치
cat dags/sample_etl_dag.py
```

### Step-07-02: Helm values 에 git repo 주소 설정
```yaml
# helm-values/airflow-values.yaml
dags:
  gitSync:
    repo: https://github.com/YOUR-ORG/YOUR-DAGS-REPO.git
    branch: main
    subPath: "dags"
```

설정 변경 후 Helm 업그레이드:
```bash
helm upgrade airflow apache-airflow/airflow \
  --namespace airflow \
  --values helm-values/airflow-values.yaml
```

### Step-07-03: GitSync 상태 확인
```bash
# Scheduler Pod 의 git-sync 사이드카 로그 확인
kubectl logs -n airflow \
  $(kubectl get pods -n airflow -l component=scheduler -o jsonpath='{.items[0].metadata.name}') \
  -c git-sync --tail=30
```

---

## Step-08: 샘플 DAG 실행 및 확인

### Step-08-01: Web UI 에서 DAG 활성화
1. 브라우저에서 Airflow Web UI 접속
2. DAG 목록에서 `sample_etl_dag` 확인
3. 토글(▶)로 DAG 활성화
4. "Trigger DAG" 버튼으로 수동 실행

### Step-08-02: kubectl 로 Worker Pod 확인
```bash
# DAG 실행 중 KubernetesExecutor 가 생성한 Worker Pod 실시간 확인
kubectl get pods -n airflow -w

# 완료된 Worker Pod 포함 전체 확인
kubectl get pods -n airflow --field-selector=status.phase=Succeeded
kubectl get pods -n airflow --field-selector=status.phase=Failed

# 특정 태스크 Pod 로그 확인
kubectl logs -n airflow <worker-pod-name>
```

### Step-08-03: 태스크 로그 확인 (Web UI)
- Web UI → DAGs → `sample_etl_dag` → Graph/Grid View
- 각 태스크 클릭 → **Log** 탭에서 실행 로그 확인

---

## Step-09: KubernetesExecutor 심화 기술 설명

### 9-1. 내부 동작 시퀀스

KubernetesExecutor 는 Airflow Scheduler 내부에 내장된 Kubernetes 클라이언트입니다.  
별도의 Worker 프로세스나 Redis/RabbitMQ 없이, **Kubernetes API Server 에 직접 Pod 생성을 요청**합니다.

```
┌──────────────────────────────────────────────────────────────────┐
│ Airflow Scheduler Pod                                            │
│                                                                  │
│  1. DAG 파싱 스레드                                              │
│     └─ git-sync 사이드카가 /opt/airflow/dags 에 동기화한         │
│        Python 파일을 읽어 실행할 태스크 목록 계산               │
│                                                                  │
│  2. Task Instance 상태 관리 (메타데이터 DB ← MariaDB Pod)        │
│     └─ scheduled → queued → running → success/failed            │
│                                                                  │
│  3. KubernetesExecutor._process_tasks()                          │
│     └─ queued 상태 태스크 감지                                   │
│     └─ kubernetes.client.CoreV1Api.create_namespaced_pod() 호출  │
│                                                                  │
│  4. Worker Pod 완료 감지 (Watch API)                              │
│     └─ Pod 상태 Succeeded → Task Instance 를 success 로 갱신   │
│     └─ Pod 상태 Failed    → Task Instance 를 failed 로 갱신     │
│     └─ delete_worker_pods: True 이면 Pod 자동 삭제              │
└──────────────────────────────────────────────────────────────────┘
         │  Kubernetes API (in-cluster config)
         ▼
┌──────────────────────────────────────────────────────────────────┐
│ EKS API Server                                                   │
│  create Pod → kube-scheduler → 노드 배정 → kubelet → 컨테이너  │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│ Worker Pod (수명: 태스크 실행 시간만큼)                           │
│  image: apache/airflow:2.9.3                                     │
│  command: airflow tasks run <dag_id> <task_id> <run_id>          │
│  envs: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=mysql+mysqldb://...   │
│        AIRFLOW__CORE__EXECUTOR=KubernetesExecutor                │
└──────────────────────────────────────────────────────────────────┘
```

### 9-2. Worker Pod 네이밍 규칙

Airflow 가 생성하는 Worker Pod 이름은 다음 규칙을 따릅니다:

```
<dag-id>-<task-id>-<run-id-hash>-<random>

예시:
  sample-etl-dag-extract-20250101t000000-a3f2c1
  sample-etl-dag-transform-20250101t000000-b7e9d4
  sample-etl-dag-load-20250101t000000-c1a8f2
```

```bash
# 실행 중인 Worker Pod 확인 (component=worker 레이블)
kubectl get pods -n airflow -l airflow-worker=true

# Pod 이름으로 어떤 태스크인지 확인
kubectl get pods -n airflow -o custom-columns=\
"NAME:.metadata.name,DAG:.metadata.labels.dag_id,TASK:.metadata.labels.task_id,STATUS:.status.phase"
```

### 9-3. RBAC — Scheduler 의 권한 요구사항

Scheduler 가 Kubernetes API 를 호출하려면 적절한 RBAC 권한이 필요합니다.  
Airflow Helm Chart 는 설치 시 이 권한을 자동으로 구성합니다.

```yaml
# Helm Chart 가 자동 생성하는 ClusterRole (핵심 권한)
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["create", "get", "list", "watch", "delete", "patch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: ["create", "get"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["list"]
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch"]
```

```bash
# Helm Chart 가 생성한 ServiceAccount 확인
kubectl get serviceaccount -n airflow

# Scheduler 의 ClusterRoleBinding 확인
kubectl get rolebinding -n airflow
kubectl get clusterrolebinding | grep airflow

# Scheduler 가 실제로 Pod 를 생성할 수 있는지 권한 확인
kubectl auth can-i create pods \
  --namespace airflow \
  --as system:serviceaccount:airflow:airflow-scheduler
```

### 9-4. Worker Pod 에 전달되는 환경변수

Scheduler 는 Worker Pod 를 생성할 때 메타데이터 DB 연결 정보 등을  
**환경변수**로 자동 주입합니다.

```bash
# 실행 중인 Worker Pod 의 환경변수 확인
kubectl exec -n airflow <worker-pod-name> -- env | grep AIRFLOW

# 주요 환경변수:
# AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
#   = mysql+mysqldb://airflow:airflow123!@mariadb.airflow.svc.cluster.local:3306/airflow_meta
# AIRFLOW__CORE__EXECUTOR       = KubernetesExecutor
# AIRFLOW__CORE__FERNET_KEY     = (암호화된 Fernet 키)
# AIRFLOW__CORE__DAGS_FOLDER    = /opt/airflow/dags
```

Worker Pod 는 메타데이터 DB(MariaDB)에 직접 연결하여  
태스크 실행 결과(시작시간, 완료시간, 상태, 로그 경로)를 기록합니다.

### 9-5. DAG 파일 전달 방식 (GitSync 사이드카)

KubernetesExecutor 에서는 Scheduler 와 Worker Pod 가 **다른 Pod** 이므로,  
DAG 파일을 Worker 에도 전달해야 합니다.

```
Scheduler Pod                     Worker Pod
┌─────────────────────┐           ┌─────────────────────┐
│ git-sync (sidecar)  │           │ git-sync (sidecar)  │
│   └─ /dags 동기화   │           │   └─ /dags 동기화   │
│                     │           │                     │
│ airflow-scheduler   │           │ airflow-worker      │
│   └─ /dags 읽기     │           │   └─ /dags 읽기     │
└─────────────────────┘           └─────────────────────┘
         ↕                                 ↕
    git remote (GitHub 등)          git remote (동일 repo)
```

Worker Pod 도 **자체 git-sync 사이드카**를 포함하여 기동합니다.  
이 때문에 `dags.gitSync.enabled: true` 설정이 Worker 에도 적용됩니다.

```bash
# Worker Pod 의 git-sync 사이드카 로그 확인
kubectl logs -n airflow <worker-pod-name> -c git-sync
```

### 9-6. 리소스 격리와 제한

각 태스크는 독립 Pod 에서 실행되므로, 태스크별 CPU/메모리 제한이 가능합니다.

```python
# DAG 코드에서 태스크별 Pod 리소스 직접 지정
from airflow.kubernetes.pod import Resources

with dag:
    heavy_task = BashOperator(
        task_id="heavy_task",
        bash_command="python heavy_processing.py",
        executor_config={
            "pod_override": k8s.V1Pod(
                spec=k8s.V1PodSpec(
                    containers=[
                        k8s.V1Container(
                            name="base",
                            resources=k8s.V1ResourceRequirements(
                                requests={"cpu": "2", "memory": "4Gi"},
                                limits={"cpu": "4", "memory": "8Gi"},
                            ),
                        )
                    ]
                )
            )
        },
    )
```

### 9-7. Worker Pod 라이프사이클과 상태 흐름

```
[Scheduler 가 태스크 감지]
        │
        ▼
  ┌───────────┐
  │  queued   │  ← Scheduler 가 Kubernetes API 로 Pod 생성 요청
  └─────┬─────┘
        │ Pod Pending (노드 배정 대기, 이미지 Pull 등)
        ▼
  ┌───────────┐
  │  running  │  ← Pod Running, airflow tasks run 명령 실행 중
  └─────┬─────┘
        │
        ├── 성공 → Pod Succeeded → Task Instance: success
        │                          (delete_worker_pods: True 이면 Pod 삭제)
        │
        └── 실패 → Pod Failed    → Task Instance: failed
                                   (delete_worker_pods_on_failure: False
                                    이면 Pod 유지 → 로그 확인 가능)
```

```bash
# 실패한 Worker Pod 로그 확인 (delete_worker_pods_on_failure: False 설정 시)
kubectl get pods -n airflow --field-selector=status.phase=Failed
kubectl logs -n airflow <failed-worker-pod-name>

# 태스크 재실행 (Web UI 또는 CLI)
kubectl exec -n airflow <scheduler-pod-name> -- \
  airflow tasks clear sample_etl_dag -t extract -s 2025-01-01 -y
```

### 9-8. CeleryExecutor 와 비교

| 항목 | KubernetesExecutor | CeleryExecutor |
|------|-------------------|---------------|
| Worker 방식 | 태스크마다 Pod 동적 생성·소멸 | 상시 Worker Pod 유지 |
| 리소스 효율 | 높음 (유휴 Worker 없음) | 낮음 (상시 대기 비용) |
| 태스크 격리 | 완전 격리 (Pod 단위, OS/패키지 분리) | 프로세스 수준 격리 |
| 실행 지연 | 수 초 (Pod 기동 시간) | 수백 ms |
| 메시지 브로커 | ❌ 불필요 (Kubernetes API 직접 사용) | ✅ Redis / RabbitMQ 필요 |
| 태스크별 이미지 | ✅ 다른 이미지 사용 가능 | ❌ 동일 Worker 이미지 |
| 태스크별 리소스 제한 | ✅ Pod spec 으로 세밀 제어 | ❌ Worker 전체 공유 |
| 적합한 환경 | 배치성·간헐적·이기종 워크로드 | 고빈도·저지연 워크로드 |
| Kubernetes 의존도 | 강함 (Kubernetes 필수) | 약함 |

### 9-9. 자주 발생하는 문제와 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| Worker Pod 가 Pending 으로 멈춤 | 노드 리소스 부족 / 이미지 Pull 실패 | `kubectl describe pod <worker>` 로 Events 확인 |
| "No module named ..." 오류 | Worker 이미지에 패키지 없음 | 커스텀 이미지 빌드 또는 `_PIP_ADDITIONAL_REQUIREMENTS` 사용 |
| DB 연결 오류 | MariaDB DNS 해석 실패 | `nslookup mariadb.airflow.svc.cluster.local` 확인 |
| RBAC 권한 오류 | ServiceAccount 권한 부족 | `kubectl auth can-i create pods --as ...` 확인 |
| DAG 가 Worker 에 보이지 않음 | git-sync 사이드카 오류 | Worker Pod 의 git-sync 컨테이너 로그 확인 |

```bash
# KubernetesExecutor 관련 Scheduler 로그만 필터링
kubectl logs -n airflow \
  $(kubectl get pods -n airflow -l component=scheduler -o jsonpath='{.items[0].metadata.name}') \
  | grep -E "KubernetesExecutor|worker_pod|create_pod|pod_id"
```

---

## Step-10: Airflow 버전 업그레이드

```bash
# 최신 차트 버전 확인
helm repo update
helm search repo apache-airflow/airflow --versions | head -5

# values 파일의 worker_container_tag 도 함께 업데이트 후 적용
helm upgrade airflow apache-airflow/airflow \
  --namespace airflow \
  --values helm-values/airflow-values.yaml \
  --timeout 10m0s
```

---

## Step-11: 정리

```bash
# Airflow Helm release 삭제
helm uninstall airflow --namespace airflow

# MariaDB 리소스 삭제
kubectl delete -f kube-manifests/06-airflow-ingress.yaml
kubectl delete -f kube-manifests/05-mariadb-service.yaml
kubectl delete -f kube-manifests/04-mariadb-statefulset.yaml
kubectl delete -f kube-manifests/03-mariadb-secret.yaml

# PVC 삭제 (데이터 영구 삭제 — 주의!)
kubectl delete pvc -n airflow --all

# StorageClass / Namespace 삭제
kubectl delete -f kube-manifests/02-storage-class.yaml
kubectl delete -f kube-manifests/01-namespace.yaml

# PV 확인 (Released 상태 PV 수동 삭제)
kubectl get pv | grep airflow
```

---

## 참고 자료

- [Apache Airflow 공식 문서](https://airflow.apache.org/docs/)
- [Airflow Helm Chart 문서](https://airflow.apache.org/docs/helm-chart/)
- [Airflow on Kubernetes 설정 가이드](https://airflow.apache.org/docs/apache-airflow/stable/executor/kubernetes.html)
- [Airflow KubernetesExecutor](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/executor/kubernetes.html)
- [GitSync 설정](https://airflow.apache.org/docs/helm-chart/stable/manage-dags-files.html)
- [MariaDB + Airflow 연동](https://airflow.apache.org/docs/apache-airflow/stable/howto/set-up-database.html)
- [ArtifactHub: apache-airflow/airflow](https://artifacthub.io/packages/helm/apache-airflow/airflow)
