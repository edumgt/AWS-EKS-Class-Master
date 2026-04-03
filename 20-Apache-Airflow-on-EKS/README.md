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

## Step-09: KubernetesExecutor 동작 원리

```
Scheduler
  │
  ├─ DAG 파싱 (git-sync 사이드카가 /opt/airflow/dags 에 자동 동기화)
  │
  └─ 태스크 실행 시점
       │
       ├─ Kubernetes API 호출: Worker Pod 생성 요청
       │     image: apache/airflow:2.9.3
       │     namespace: airflow
       │     envs: AIRFLOW__CORE__EXECUTOR=KubernetesExecutor
       │
       ├─ Worker Pod 실행 (태스크 코드 실행)
       │
       └─ 완료 후 Worker Pod 자동 삭제 (delete_worker_pods: True)
```

### CeleryExecutor 와 비교

| 항목 | KubernetesExecutor | CeleryExecutor |
|------|-------------------|---------------|
| Worker 방식 | 태스크마다 Pod 동적 생성 | 상시 Worker Pod 유지 |
| 리소스 효율 | 높음 (유휴 Worker 없음) | 낮음 (상시 대기 비용) |
| 태스크 격리 | 완전 격리 (Pod 단위) | 프로세스 수준 격리 |
| 실행 지연 | 약간 있음 (Pod 기동 시간) | 낮음 |
| 적합한 환경 | 배치성·간헐적 워크로드 | 고빈도·저지연 워크로드 |
| Redis 필요 | ❌ 불필요 | ✅ 필요 |

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
