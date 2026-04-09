"""
FastAPI Backend for Dynamic Jupyter Lab Pod Management with HPA
사용자 증가에 따라 Jupyter Lab Pod를 동적으로 생성/관리하는 백엔드
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect, Path, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
import os
import hashlib
import time
import logging
from typing import Dict, Optional
import asyncio
from datetime import datetime
from urllib.parse import urlencode, parse_qsl
import re
import secrets

import httpx
import websockets

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jupyter Lab Pod Manager",
    description="HPA를 지원하는 동적 Jupyter Lab Pod 관리 시스템",
    version="1.0.0"
)

# Kubernetes 클라이언트 초기화
try:
    # 클러스터 내부에서 실행 시
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes config")
except:
    # 로컬 개발 환경
    config.load_kube_config()
    logger.info("Loaded local Kubernetes config")

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
custom_api = client.CustomObjectsApi()
security = HTTPBasic()

# 환경 변수
NAMESPACE = os.getenv("NAMESPACE", "default")
JUPYTER_IMAGE = os.getenv("JUPYTER_IMAGE", "jupyter/minimal-notebook:latest")
JUPYTER_PVC_SIZE = os.getenv("JUPYTER_PVC_SIZE", "5Gi")
JUPYTER_STORAGE_CLASS = os.getenv("JUPYTER_STORAGE_CLASS", "").strip()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")
MAX_CONCURRENT_JUPYTER_PODS = int(os.getenv("MAX_CONCURRENT_JUPYTER_PODS", "9"))
QUEUE_SLOT_MINUTES = int(os.getenv("QUEUE_SLOT_MINUTES", "15"))

# 활성 사용자 세션 저장소 (실제 환경에서는 Redis 등 사용)
active_sessions: Dict[str, Dict] = {}


class UserRequest(BaseModel):
    username: str


class SessionResponse(BaseModel):
    session_id: str
    username: str
    jupyter_url: str
    access_url: str
    pod_name: str
    status: str
    can_launch: bool
    queue_position: Optional[int] = None
    estimated_wait_seconds: int = 0


class CreateSessionByUserResponse(BaseModel):
    user_id: str
    session_id: str
    launch_url: str
    status_url: str
    delete_url: str
    status: str
    can_launch: bool
    queue_position: Optional[int] = None
    estimated_wait_seconds: int = 0


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    valid_user = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    valid_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (valid_user and valid_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/")
async def root():
    """헬스 체크 엔드포인트"""
    return {
        "service": "Jupyter Lab Pod Manager",
        "status": "running",
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """헬스 체크 (Kubernetes Probes용)"""
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """메트릭 엔드포인트 (모니터링용)"""
    return {
        "active_sessions": len(active_sessions),
        "sessions": list(active_sessions.keys())
    }


def build_proxy_base(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{forwarded_proto}://{forwarded_host}"


def normalize_user_id(username: str) -> str:
    value = re.sub(r"[^a-z0-9-]", "-", username.lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "user"


def make_pvc_name(normalized_user: str) -> str:
    return f"jupyter-work-{normalized_user}"


def make_session_record(
    request: Request,
    username: str,
    session_id: str,
    pod_name: str,
    service_name: str,
    status: str,
    created_at: str,
    pvc_name: str
) -> Dict:
    proxy_base = build_proxy_base(request)
    return {
        "session_id": session_id,
        "username": username,
        "pod_name": pod_name,
        "service_name": service_name,
        "jupyter_url": f"http://{service_name}.{NAMESPACE}.svc.cluster.local:8888/user/{session_id}/lab?token={session_id}",
        "access_url": f"{proxy_base}/lab?sessionid={session_id}",
        "created_at": created_at,
        "status": status,
        "pvc_name": pvc_name
    }


def count_active_jupyter_pods() -> int:
    pods = v1.list_namespaced_pod(namespace=NAMESPACE, label_selector="app=jupyter-lab")
    return sum(1 for pod in pods.items if pod.status.phase not in {"Succeeded", "Failed"})


def get_queued_session_ids() -> list[str]:
    queued = [
        (session_id, info)
        for session_id, info in active_sessions.items()
        if info.get("status") == "queued"
    ]
    queued.sort(key=lambda item: item[1].get("queued_at", item[1].get("created_at", "")))
    return [session_id for session_id, _ in queued]


def refresh_queue_metadata():
    for index, session_id in enumerate(get_queued_session_ids(), start=1):
        active_sessions[session_id]["queue_position"] = index
        active_sessions[session_id]["estimated_wait_seconds"] = index * QUEUE_SLOT_MINUTES * 60


def mark_session_as_queued(record: Dict):
    record["status"] = "queued"
    record["queued_at"] = datetime.now().isoformat()
    record["queue_position"] = None
    record["estimated_wait_seconds"] = 0
    refresh_queue_metadata()


def build_session_response(record: Dict) -> SessionResponse:
    return SessionResponse(
        session_id=record["session_id"],
        username=record["username"],
        jupyter_url=record["jupyter_url"],
        access_url=record["access_url"],
        pod_name=record["pod_name"],
        status=record["status"],
        can_launch=record["status"] == "running",
        queue_position=record.get("queue_position"),
        estimated_wait_seconds=record.get("estimated_wait_seconds", 0)
    )


def parse_cpu_to_millicores(value: str) -> int:
    if value.endswith("n"):
        return max(1, int(value[:-1]) // 1_000_000)
    if value.endswith("u"):
        return max(1, int(value[:-1]) // 1_000)
    if value.endswith("m"):
        return int(value[:-1])
    return int(float(value) * 1000)


def parse_memory_to_mib(value: str) -> int:
    units = {
        "Ki": 1 / 1024,
        "Mi": 1,
        "Gi": 1024,
        "Ti": 1024 * 1024,
        "K": 1 / 1000,
        "M": 1 / (1000 / 1024 / 1024),
        "G": 1000,
    }
    for suffix, factor in units.items():
        if value.endswith(suffix):
            return int(float(value[:-len(suffix)]) * factor)
    return int(int(value) / (1024 * 1024))


def get_pod_metrics_map() -> Dict[str, Dict[str, int]]:
    metrics = {}
    try:
        response = custom_api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=NAMESPACE,
            plural="pods"
        )
        for item in response.get("items", []):
            total_cpu = 0
            total_mem = 0
            for container in item.get("containers", []):
                usage = container.get("usage", {})
                total_cpu += parse_cpu_to_millicores(usage.get("cpu", "0m"))
                total_mem += parse_memory_to_mib(usage.get("memory", "0Mi"))
            metrics[item["metadata"]["name"]] = {
                "cpu_millicores": total_cpu,
                "memory_mib": total_mem
            }
    except ApiException as exc:
        logger.warning("Unable to fetch pod metrics: %s", exc)
    return metrics


def get_disk_usage_for_pod(pod_name: str) -> Dict[str, str]:
    try:
        output = stream(
            v1.connect_get_namespaced_pod_exec,
            pod_name,
            NAMESPACE,
            command=["sh", "-lc", "df -k /home/jovyan/work | tail -n 1"],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        ).strip()
        parts = output.split()
        if len(parts) >= 5:
            used_kb = int(parts[2])
            avail_kb = int(parts[3])
            pct = parts[4]
            return {
                "disk_used_gib": f"{used_kb / 1024 / 1024:.2f}",
                "disk_available_gib": f"{avail_kb / 1024 / 1024:.2f}",
                "disk_usage_percent": pct
            }
    except Exception as exc:
        logger.warning("Unable to fetch disk usage for %s: %s", pod_name, exc)
    return {
        "disk_used_gib": "-",
        "disk_available_gib": "-",
        "disk_usage_percent": "-"
    }


def collect_jupyter_usage_rows(request: Request) -> list[Dict]:
    proxy_base = build_proxy_base(request)
    metrics_map = get_pod_metrics_map()
    pods = v1.list_namespaced_pod(namespace=NAMESPACE, label_selector="app=jupyter-lab")
    rows = []

    for pod in pods.items:
        labels = pod.metadata.labels or {}
        session_id = labels.get("session", "")
        username = labels.get("original-user", labels.get("user", "unknown"))
        pod_name = pod.metadata.name
        service_name = f"svc-{pod_name}"
        created_at = pod.metadata.creation_timestamp
        created_iso = created_at.isoformat() if created_at else datetime.now().isoformat()
        duration_seconds = max(0, int((datetime.now().astimezone() - created_at).total_seconds())) if created_at else 0
        pod_phase = "running" if pod.status.phase == "Running" else pod.status.phase.lower()
        metric = metrics_map.get(pod_name, {})
        disk = get_disk_usage_for_pod(pod_name) if pod.status.phase == "Running" else {
            "disk_used_gib": "-",
            "disk_available_gib": "-",
            "disk_usage_percent": "-"
        }
        rows.append({
            "username": username,
            "session_id": session_id,
            "pod_name": pod_name,
            "status": pod_phase,
            "launch_url": f"{proxy_base}/lab?sessionid={session_id}" if session_id else "-",
            "created_at": created_iso,
            "usage_minutes": round(duration_seconds / 60, 1),
            "cpu_millicores": metric.get("cpu_millicores", 0),
            "memory_mib": metric.get("memory_mib", 0),
            "disk_used_gib": disk["disk_used_gib"],
            "disk_available_gib": disk["disk_available_gib"],
            "disk_usage_percent": disk["disk_usage_percent"],
            "pvc_name": make_pvc_name(labels.get("user", normalize_user_id(username)))
        })
    return rows


def ensure_user_pvc(username: str) -> str:
    normalized_user = normalize_user_id(username)
    pvc_name = make_pvc_name(normalized_user)

    try:
        v1.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=NAMESPACE)
        return pvc_name
    except ApiException as exc:
        if exc.status != 404:
            raise

    resources = client.V1ResourceRequirements(
        requests={"storage": JUPYTER_PVC_SIZE}
    )
    spec = client.V1PersistentVolumeClaimSpec(
        access_modes=["ReadWriteOnce"],
        resources=resources
    )
    if JUPYTER_STORAGE_CLASS:
        spec.storage_class_name = JUPYTER_STORAGE_CLASS

    pvc = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(
            name=pvc_name,
            labels={
                "app": "jupyter-lab-storage",
                "user": normalized_user
            }
        ),
        spec=spec
    )
    v1.create_namespaced_persistent_volume_claim(namespace=NAMESPACE, body=pvc)
    logger.info("Created PVC %s for user %s", pvc_name, username)
    return pvc_name


def find_existing_session_for_user(username: str, request: Request) -> Dict | None:
    normalized_user = normalize_user_id(username)
    pods = v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=f"app=jupyter-lab,user={normalized_user}"
    )

    for pod in pods.items:
        session_id = (pod.metadata.labels or {}).get("session")
        if not session_id:
            continue
        service_name = f"svc-{pod.metadata.name}"
        try:
            v1.read_namespaced_service(name=service_name, namespace=NAMESPACE)
        except ApiException:
            continue

        status = "running" if pod.status.phase == "Running" else pod.status.phase.lower()
        created_at = (
            pod.metadata.creation_timestamp.isoformat()
            if pod.metadata.creation_timestamp else datetime.now().isoformat()
        )
        record = make_session_record(
            request=request,
            username=username,
            session_id=session_id,
            pod_name=pod.metadata.name,
            service_name=service_name,
            status=status,
            created_at=created_at,
            pvc_name=make_pvc_name(normalized_user)
        )
        active_sessions[session_id] = record
        record["queue_position"] = None
        record["estimated_wait_seconds"] = 0
        return record
    return None


def hydrate_session_from_cluster(session_id: str) -> Dict | None:
    pods = v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=f"app=jupyter-lab,session={session_id}"
    )
    if not pods.items:
        return None

    pod = pods.items[0]
    labels = pod.metadata.labels or {}
    username = labels.get("original-user", labels.get("user", "unknown"))
    service_name = f"svc-{pod.metadata.name}"
    try:
        v1.read_namespaced_service(name=service_name, namespace=NAMESPACE)
    except ApiException:
        return None

    status = "running" if pod.status.phase == "Running" else pod.status.phase.lower()
    record = {
        "session_id": session_id,
        "username": username,
        "pod_name": pod.metadata.name,
        "service_name": service_name,
        "jupyter_url": f"http://{service_name}.{NAMESPACE}.svc.cluster.local:8888/user/{session_id}/lab?token={session_id}",
        "access_url": "",
        "created_at": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else datetime.now().isoformat(),
        "status": status,
        "pvc_name": make_pvc_name(labels.get("user", normalize_user_id(username))),
        "queue_position": None,
        "estimated_wait_seconds": 0
    }
    active_sessions[session_id] = record
    return record


def get_session_or_404(session_id: str) -> Dict:
    session = active_sessions.get(session_id)
    if not session:
        session = hydrate_session_from_cluster(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def create_jupyter_resources(username: str, session_id: str, pvc_name: str) -> tuple[str, str]:
    normalized_user = normalize_user_id(username)
    pod_name = f"jupyter-{normalized_user}-{session_id}"
    service_name = f"svc-{pod_name}"

    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name,
            labels={
                "app": "jupyter-lab",
                "user": normalized_user,
                "original-user": username,
                "session": session_id
            }
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="jupyter",
                    image=JUPYTER_IMAGE,
                    ports=[client.V1ContainerPort(container_port=8888)],
                    env=[
                        client.V1EnvVar(name="JUPYTER_ENABLE_LAB", value="yes"),
                        client.V1EnvVar(name="JUPYTER_TOKEN", value=session_id)
                    ],
                    args=[
                        "start-notebook.py",
                        f"--ServerApp.base_url=/user/{session_id}/",
                        f"--ServerApp.token={session_id}",
                        "--ServerApp.allow_origin=*",
                        "--ServerApp.trust_xheaders=True",
                        "--ServerApp.allow_remote_access=True"
                    ],
                    resources=client.V1ResourceRequirements(
                        requests={"memory": "512Mi", "cpu": "250m"},
                        limits={"memory": "1Gi", "cpu": "500m"}
                    ),
                    volume_mounts=[
                        client.V1VolumeMount(
                            name="jupyter-workspace",
                            mount_path="/home/jovyan/work"
                        )
                    ]
                )
            ],
            volumes=[
                client.V1Volume(
                    name="jupyter-workspace",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=pvc_name
                    )
                )
            ]
        )
    )
    v1.create_namespaced_pod(namespace=NAMESPACE, body=pod)

    service = client.V1Service(
        metadata=client.V1ObjectMeta(
            name=service_name,
            labels={"app": "jupyter-lab", "session": session_id}
        ),
        spec=client.V1ServiceSpec(
            selector={"session": session_id},
            ports=[client.V1ServicePort(port=8888, target_port=8888)],
            type="ClusterIP"
        )
    )
    v1.create_namespaced_service(namespace=NAMESPACE, body=service)
    return pod_name, service_name


def try_start_queued_sessions():
    refresh_queue_metadata()

    while count_active_jupyter_pods() < MAX_CONCURRENT_JUPYTER_PODS:
        queued_session_ids = get_queued_session_ids()
        if not queued_session_ids:
            return

        session_id = queued_session_ids[0]
        record = active_sessions.get(session_id)
        if not record:
            refresh_queue_metadata()
            continue

        try:
            pod_name, service_name = create_jupyter_resources(
                username=record["username"],
                session_id=session_id,
                pvc_name=record["pvc_name"]
            )
        except ApiException as exc:
            logger.error("Failed to promote queued session %s: %s", session_id, exc)
            record["status"] = "error"
            record["estimated_wait_seconds"] = 0
            record["queue_position"] = None
            refresh_queue_metadata()
            return

        record["pod_name"] = pod_name
        record["service_name"] = service_name
        record["jupyter_url"] = (
            f"http://{service_name}.{NAMESPACE}.svc.cluster.local:8888/user/{session_id}/lab?token={session_id}"
        )
        record["status"] = "creating"
        record["queue_position"] = None
        record["estimated_wait_seconds"] = 0
        record.pop("queued_at", None)
        asyncio.create_task(wait_for_pod_ready(session_id, pod_name))
        refresh_queue_metadata()


def build_upstream_http_url(session_info: Dict, path: str, query_params) -> str:
    query_items = list(query_params.multi_items())
    if not any(key == "token" for key, _ in query_items):
        query_items.append(("token", session_info["session_id"]))
    base_path = f"/user/{session_info['session_id']}/{path}".rstrip("/")
    if path == "":
        base_path = f"/user/{session_info['session_id']}/"
    url = f"http://{session_info['service_name']}.{NAMESPACE}.svc.cluster.local:8888{base_path}"
    encoded = urlencode(query_items)
    if encoded:
        return f"{url}?{encoded}"
    return url


def build_upstream_ws_url(session_info: Dict, path: str, query_string: str) -> str:
    base = f"ws://{session_info['service_name']}.{NAMESPACE}.svc.cluster.local:8888/user/{session_info['session_id']}/{path}"
    query_items = parse_qsl(query_string, keep_blank_values=True)
    if not any(key == "token" for key, _ in query_items):
        query_items.append(("token", session_info["session_id"]))
    encoded = urlencode(query_items)
    if encoded:
        return f"{base}?{encoded}"
    return base


async def create_session_for_username(
    username: str,
    background_tasks: BackgroundTasks,
    request: Request
) -> SessionResponse:
    """공통 세션 생성 로직"""
    existing = find_existing_session_for_user(username, request)
    if existing:
        logger.info("Reusing existing Jupyter session %s for user %s", existing["session_id"], username)
        existing["queue_position"] = None
        existing["estimated_wait_seconds"] = 0
        return build_session_response(existing)

    # 세션 ID 생성
    session_id = hashlib.md5(f"{username}-{time.time()}".encode()).hexdigest()[:12]
    pvc_name = ensure_user_pvc(username)
    placeholder_service = f"svc-jupyter-{normalize_user_id(username)}-{session_id}"
    placeholder_pod = f"jupyter-{normalize_user_id(username)}-{session_id}"

    try:
        # 세션 정보 저장
        record = make_session_record(
            request=request,
            username=username,
            session_id=session_id,
            pod_name=placeholder_pod,
            service_name=placeholder_service,
            status="queued",
            created_at=datetime.now().isoformat(),
            pvc_name=pvc_name
        )
        active_sessions[session_id] = record
        mark_session_as_queued(record)

        if count_active_jupyter_pods() < MAX_CONCURRENT_JUPYTER_PODS:
            try_start_queued_sessions()

        logger.info("Accepted Jupyter session request for user %s with status %s", username, active_sessions[session_id]["status"])
        return build_session_response(active_sessions[session_id])
        
    except ApiException as e:
        logger.error(f"Failed to create pod: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create Jupyter Lab pod: {e}")


@app.post(
    "/session/create",
    response_model=SessionResponse,
    tags=["Sessions"],
    summary="Create a Jupyter session from request body",
    description="요청 본문의 username 값으로 사용자 전용 Jupyter Lab Pod를 생성합니다."
)
async def create_session(user: UserRequest, background_tasks: BackgroundTasks, request: Request):
    return await create_session_for_username(user.username, background_tasks, request)


@app.post(
    "/users/{user_id}/session",
    response_model=CreateSessionByUserResponse,
    tags=["Users"],
    summary="Create a Jupyter session for a user ID",
    description=(
        "Swagger에서 user_id path parameter만 넣고 실행할 수 있는 사용자별 세션 생성 API입니다. "
        "응답의 launch_url을 브라우저에서 열면 `/lab?sessionid=xxxx` 형식으로 Jupyter Lab에 진입합니다."
    )
)
async def create_session_for_user_id(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Path(..., description="세션을 생성할 사용자 ID", examples=["alice01"])
):
    session = await create_session_for_username(user_id, background_tasks, request)
    proxy_base = build_proxy_base(request)
    return CreateSessionByUserResponse(
        user_id=user_id,
        session_id=session.session_id,
        launch_url=session.access_url,
        status_url=f"{proxy_base}/session/{session.session_id}",
        delete_url=f"{proxy_base}/session/{session.session_id}",
        status=session.status,
        can_launch=session.can_launch,
        queue_position=session.queue_position,
        estimated_wait_seconds=session.estimated_wait_seconds
    )


async def wait_for_pod_ready(session_id: str, pod_name: str):
    """Pod가 Ready 상태가 될 때까지 대기"""
    max_wait = 300  # 5분
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            pod = v1.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
            if pod.status.phase == "Running":
                active_sessions[session_id]["status"] = "running"
                active_sessions[session_id]["queue_position"] = None
                active_sessions[session_id]["estimated_wait_seconds"] = 0
                logger.info(f"Pod {pod_name} is now running")
                return
        except ApiException:
            pass
        
        await asyncio.sleep(5)
    
    # 타임아웃
    active_sessions[session_id]["status"] = "timeout"
    logger.warning(f"Pod {pod_name} did not become ready in time")
    try_start_queued_sessions()


@app.get(
    "/session/{session_id}",
    tags=["Sessions"],
    summary="Get session details"
)
async def get_session(session_id: str):
    """세션 정보 조회"""
    try_start_queued_sessions()
    session_info = get_session_or_404(session_id)
    return {
        **session_info,
        "can_launch": session_info["status"] == "running",
        "queue_position": session_info.get("queue_position"),
        "estimated_wait_seconds": session_info.get("estimated_wait_seconds", 0)
    }


@app.get(
    "/sessions",
    tags=["Sessions"],
    summary="List active sessions"
)
async def list_sessions():
    """모든 활성 세션 목록"""
    try_start_queued_sessions()
    return {
        "total": len(active_sessions),
        "sessions": active_sessions
    }


@app.get(
    "/admin/usage",
    tags=["Admin"],
    summary="List all Jupyter usage rows",
    dependencies=[Depends(require_admin)]
)
async def admin_usage(request: Request):
    rows = collect_jupyter_usage_rows(request)
    return {
        "total": len(rows),
        "rows": rows
    }


@app.delete(
    "/session/{session_id}",
    tags=["Sessions"],
    summary="Delete a session"
)
async def delete_session(session_id: str):
    """사용자 세션 및 Jupyter Lab Pod 삭제"""
    session_info = get_session_or_404(session_id)
    pod_name = session_info["pod_name"]
    service_name = session_info["service_name"]
    
    try:
        if session_info["status"] != "queued":
            v1.delete_namespaced_pod(name=pod_name, namespace=NAMESPACE)
            logger.info(f"Deleted pod: {pod_name}")
            v1.delete_namespaced_service(name=service_name, namespace=NAMESPACE)
            logger.info(f"Deleted service: {service_name}")
        
        # 세션 정보 제거
        del active_sessions[session_id]
        refresh_queue_metadata()
        try_start_queued_sessions()
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except ApiException as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")


@app.get(
    "/lab",
    tags=["Launch"],
    summary="Launch Jupyter Lab by session ID",
    description="CLB 주소에서 `/lab?sessionid=xxxx` 형식으로 호출하면 해당 세션의 Jupyter Lab로 이동합니다."
)
async def launch_lab(sessionid: str):
    """CLB URL에서 sessionid로 Jupyter Lab 진입"""
    session_info = get_session_or_404(sessionid)
    if session_info["status"] != "running":
        return HTMLResponse(
            content=(
                "<html><body style='font-family: sans-serif; padding: 2rem;'>"
                f"<h2>Session {sessionid} is not ready yet</h2>"
                f"<p>Current status: {session_info['status']}</p>"
                "<p>잠시 후 새로고침하세요.</p>"
                "</body></html>"
            ),
            status_code=503
        )

    return RedirectResponse(url=f"/user/{sessionid}/lab?token={sessionid}", status_code=307)


@app.api_route("/user/{session_id}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@app.api_route("/user/{session_id}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_jupyter_http(session_id: str, request: Request, path: str = ""):
    """세션별 Jupyter Lab HTTP reverse proxy"""
    session_info = get_session_or_404(session_id)
    upstream_url = build_upstream_http_url(session_info, path, request.query_params)

    filtered_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }

    body = await request.body()

    async with httpx.AsyncClient(follow_redirects=False, timeout=300.0) as client_http:
        upstream_response = await client_http.request(
            method=request.method,
            url=upstream_url,
            headers=filtered_headers,
            content=body
        )

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in {"content-encoding", "transfer-encoding", "connection"}
    }

    return StreamingResponse(
        content=iter([upstream_response.content]),
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type")
    )


@app.websocket("/user/{session_id}/{path:path}")
async def proxy_jupyter_websocket(websocket: WebSocket, session_id: str, path: str):
    """세션별 Jupyter Lab websocket proxy"""
    session_info = get_session_or_404(session_id)
    await websocket.accept()

    upstream_url = build_upstream_ws_url(session_info, path, websocket.scope.get("query_string", b"").decode())
    headers = [
        (key, value)
        for key, value in websocket.headers.items()
        if key.lower() not in {"host", "connection", "upgrade", "sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions"}
    ]

    try:
        async with websockets.connect(upstream_url, extra_headers=headers, open_timeout=30) as upstream_ws:
            async def client_to_upstream():
                while True:
                    message = await websocket.receive()
                    if message.get("type") == "websocket.disconnect":
                        await upstream_ws.close()
                        break
                    if message.get("text") is not None:
                        await upstream_ws.send(message["text"])
                    elif message.get("bytes") is not None:
                        await upstream_ws.send(message["bytes"])

            async def upstream_to_client():
                async for message in upstream_ws:
                    if isinstance(message, bytes):
                        await websocket.send_bytes(message)
                    else:
                        await websocket.send_text(message)

            await asyncio.gather(client_to_upstream(), upstream_to_client())
    except WebSocketDisconnect:
        logger.info("Client websocket disconnected for session %s", session_id)
    except Exception as exc:
        logger.error("Websocket proxy failed for session %s: %s", session_id, exc)
        await websocket.close(code=1011)


@app.post("/load/generate")
async def generate_load():
    """
    CPU 부하 생성 (HPA 테스트용)
    fibonacci 계산으로 CPU 사용률 증가
    """
    def fibonacci(n: int) -> int:
        if n <= 1:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)
    
    # CPU 집약적 작업
    result = fibonacci(35)
    
    return {
        "message": "Load generated",
        "fibonacci_35": result,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/pods")
async def list_jupyter_pods():
    """현재 실행 중인 모든 Jupyter Pod 목록"""
    try:
        pods = v1.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector="app=jupyter-lab"
        )
        
        pod_list = []
        for pod in pods.items:
            pod_list.append({
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip,
                "node": pod.spec.node_name,
                "created": pod.metadata.creation_timestamp.isoformat()
            })
        
        return {
            "total": len(pod_list),
            "pods": pod_list
        }
        
    except ApiException as e:
        logger.error(f"Failed to list pods: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list pods: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
