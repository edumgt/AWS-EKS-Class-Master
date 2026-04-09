"""
FastAPI Backend for Dynamic Jupyter Lab Pod Management with HPA
사용자 증가에 따라 Jupyter Lab Pod를 동적으로 생성/관리하는 백엔드
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect, Path
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import hashlib
import time
import logging
from typing import Dict
import asyncio
from datetime import datetime
from urllib.parse import urlencode

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

# 환경 변수
NAMESPACE = os.getenv("NAMESPACE", "default")
JUPYTER_IMAGE = os.getenv("JUPYTER_IMAGE", "jupyter/minimal-notebook:latest")

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


class CreateSessionByUserResponse(BaseModel):
    user_id: str
    session_id: str
    launch_url: str
    status_url: str
    delete_url: str
    status: str


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


def get_session_or_404(session_id: str) -> Dict:
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def build_upstream_http_url(session_info: Dict, path: str, query_params) -> str:
    query_string = query_params
    base_path = f"/user/{session_info['session_id']}/{path}".rstrip("/")
    if path == "":
        base_path = f"/user/{session_info['session_id']}/"
    url = f"http://{session_info['service_name']}.{NAMESPACE}.svc.cluster.local:8888{base_path}"
    encoded = urlencode(list(query_string.multi_items()))
    if encoded:
        return f"{url}?{encoded}"
    return url


def build_upstream_ws_url(session_info: Dict, path: str, query_string: str) -> str:
    base = f"ws://{session_info['service_name']}.{NAMESPACE}.svc.cluster.local:8888/user/{session_info['session_id']}/{path}"
    if query_string:
        return f"{base}?{query_string}"
    return base


async def create_session_for_username(
    username: str,
    background_tasks: BackgroundTasks,
    request: Request
) -> SessionResponse:
    """공통 세션 생성 로직"""
    # 세션 ID 생성
    session_id = hashlib.md5(f"{username}-{time.time()}".encode()).hexdigest()[:12]
    pod_name = f"jupyter-{username}-{session_id}"
    
    logger.info(f"Creating Jupyter Lab pod for user: {username}")
    
    try:
        service_name = f"svc-{pod_name}"

        # Jupyter Lab Pod 정의
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name,
                labels={
                    "app": "jupyter-lab",
                    "user": username,
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
                            client.V1EnvVar(
                                name="JUPYTER_ENABLE_LAB",
                                value="yes"
                            ),
                            client.V1EnvVar(
                                name="JUPYTER_TOKEN",
                                value=session_id
                            )
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
                        )
                    )
                ]
            )
        )
        
        # Pod 생성
        v1.create_namespaced_pod(namespace=NAMESPACE, body=pod)
        
        # Service 생성 (각 Pod에 대한 개별 서비스)
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                labels={"app": "jupyter-lab", "session": session_id}
            ),
            spec=client.V1ServiceSpec(
                selector={"session": session_id},
                ports=[client.V1ServicePort(
                    port=8888,
                    target_port=8888
                )],
                type="ClusterIP"
            )
        )
        
        v1.create_namespaced_service(namespace=NAMESPACE, body=service)
        
        # 세션 정보 저장
        proxy_base = build_proxy_base(request)
        access_url = f"{proxy_base}/lab?sessionid={session_id}"
        jupyter_url = f"http://{service_name}.{NAMESPACE}.svc.cluster.local:8888/user/{session_id}/lab?token={session_id}"
        active_sessions[session_id] = {
            "session_id": session_id,
            "username": username,
            "pod_name": pod_name,
            "service_name": service_name,
            "jupyter_url": jupyter_url,
            "access_url": access_url,
            "created_at": datetime.now().isoformat(),
            "status": "creating"
        }
        
        # 백그라운드에서 Pod 상태 확인
        background_tasks.add_task(wait_for_pod_ready, session_id, pod_name)
        
        logger.info(f"Successfully created Jupyter Lab pod: {pod_name}")
        
        return SessionResponse(
            session_id=session_id,
            username=username,
            jupyter_url=jupyter_url,
            access_url=access_url,
            pod_name=pod_name,
            status="creating"
        )
        
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
        status=session.status
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
                logger.info(f"Pod {pod_name} is now running")
                return
        except ApiException:
            pass
        
        await asyncio.sleep(5)
    
    # 타임아웃
    active_sessions[session_id]["status"] = "timeout"
    logger.warning(f"Pod {pod_name} did not become ready in time")


@app.get(
    "/session/{session_id}",
    tags=["Sessions"],
    summary="Get session details"
)
async def get_session(session_id: str):
    """세션 정보 조회"""
    return get_session_or_404(session_id)


@app.get(
    "/sessions",
    tags=["Sessions"],
    summary="List active sessions"
)
async def list_sessions():
    """모든 활성 세션 목록"""
    return {
        "total": len(active_sessions),
        "sessions": active_sessions
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
        # Pod 삭제
        v1.delete_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        logger.info(f"Deleted pod: {pod_name}")
        
        # Service 삭제
        v1.delete_namespaced_service(name=service_name, namespace=NAMESPACE)
        logger.info(f"Deleted service: {service_name}")
        
        # 세션 정보 제거
        del active_sessions[session_id]
        
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
