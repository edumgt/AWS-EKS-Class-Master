"""
sample_etl_dag.py
─────────────────
EKS 위 Airflow KubernetesExecutor 로 실행되는 간단한 ETL 예제 DAG.

파이프라인 흐름:
  extract → transform → load → notify

각 태스크는 별도의 EKS Pod 로 실행됩니다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# ── DAG 기본 설정 ──────────────────────────────────────────────────────────────
default_args = {
    "owner": "eks-class",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="sample_etl_dag",
    default_args=default_args,
    description="EKS KubernetesExecutor 기반 간단한 ETL 파이프라인 예제",
    schedule_interval="@daily",       # 매일 자정 실행
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["eks", "etl", "example"],
)

# ── Task 1: Extract ────────────────────────────────────────────────────────────
extract = BashOperator(
    task_id="extract",
    bash_command="""
        echo "[EXTRACT] 데이터 추출 시작: $(date)"
        echo "소스: s3://my-data-bucket/raw/{{ ds_nodash }}/"
        # 실제 환경에서는 S3, API, DB 등에서 데이터를 가져옵니다
        echo "추출 완료: 1000 건"
    """,
    dag=dag,
)

# ── Task 2: Transform ──────────────────────────────────────────────────────────
def transform_data(**context):
    """
    XCom 을 통해 extract 태스크 결과를 받아 변환 처리합니다.
    실제 환경에서는 pandas, spark 등으로 데이터를 가공합니다.
    """
    execution_date = context["ds"]
    print(f"[TRANSFORM] 변환 시작: {execution_date}")

    # 예시: 데이터 정제 로직
    raw_count = 1000
    filtered_count = int(raw_count * 0.85)   # 15% 필터링 가정
    print(f"원본 건수: {raw_count}, 변환 후 건수: {filtered_count}")

    # XCom 으로 다음 태스크에 결과 전달
    return {"date": execution_date, "record_count": filtered_count}


transform = PythonOperator(
    task_id="transform",
    python_callable=transform_data,
    dag=dag,
)

# ── Task 3: Load ───────────────────────────────────────────────────────────────
def load_data(**context):
    """
    변환된 데이터를 목적지(DB, S3, DW 등)에 적재합니다.
    """
    ti = context["ti"]
    transform_result = ti.xcom_pull(task_ids="transform")

    record_count = transform_result["record_count"]
    target_date = transform_result["date"]

    print(f"[LOAD] {target_date} 데이터 적재 시작")
    print(f"적재 대상 건수: {record_count}")
    print("목적지: s3://my-data-bucket/processed/")
    # 실제 환경에서는 boto3, SQLAlchemy 등으로 적재 처리
    print("[LOAD] 적재 완료")


load = PythonOperator(
    task_id="load",
    python_callable=load_data,
    dag=dag,
)

# ── Task 4: Notify ─────────────────────────────────────────────────────────────
notify = BashOperator(
    task_id="notify",
    bash_command="""
        echo "[NOTIFY] ETL 파이프라인 완료: $(date)"
        echo "실행 날짜: {{ ds }}"
        echo "DAG Run ID: {{ run_id }}"
        # 실제 환경에서는 Slack, SNS, 이메일 등으로 알림 전송
        echo "알림 발송 완료"
    """,
    dag=dag,
)

# ── 태스크 의존성 설정 ─────────────────────────────────────────────────────────
extract >> transform >> load >> notify
