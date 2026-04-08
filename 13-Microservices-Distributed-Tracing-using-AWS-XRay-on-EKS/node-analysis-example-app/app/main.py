import os
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from aws_xray_sdk.core import patch_all, xray_recorder
from fastapi import FastAPI
from fastapi.responses import FileResponse


patch_all()

APP_NAME = os.getenv("APP_NAME", "node-analysis-demo")
NODE_NAME = os.getenv("NODE_NAME", "unknown-node")
HOST_IP = os.getenv("HOST_IP", "unknown-host")
POD_NAME = os.getenv("POD_NAME", "unknown-pod")
POD_NAMESPACE = os.getenv("POD_NAMESPACE", "default")
POD_IP = os.getenv("POD_IP", "unknown-pod-ip")
XRAY_DAEMON_ADDRESS = os.getenv("AWS_XRAY_DAEMON_ADDRESS", "127.0.0.1:2000")

xray_recorder.configure(
    service=APP_NAME,
    daemon_address=XRAY_DAEMON_ADDRESS,
    context_missing="LOG_ERROR",
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="X-Ray Node Analysis Demo")


def current_snapshot() -> dict[str, str]:
    return {
        "app_name": APP_NAME,
        "node_name": NODE_NAME,
        "host_ip": HOST_IP,
        "pod_name": POD_NAME,
        "pod_namespace": POD_NAMESPACE,
        "pod_ip": POD_IP,
        "xray_daemon_address": XRAY_DAEMON_ADDRESS,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def consume_cpu_for(seconds: float) -> None:
    end_time = perf_counter() + seconds
    value = 0
    while perf_counter() < end_time:
        value += 1
    if value < 0:
        raise RuntimeError("unreachable")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "xray node analysis demo",
        "analyze_endpoint": "/analyze",
        "ui_endpoint": "/ui",
        **current_snapshot(),
    }


@app.get("/ui", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "app_name": APP_NAME}


@app.get("/analyze")
def analyze(work_seconds: float = 0.2) -> dict[str, str | float]:
    snapshot = current_snapshot()
    segment = xray_recorder.begin_segment("node-analysis-request")
    try:
        if work_seconds > 0:
            consume_cpu_for(work_seconds)
        xray_recorder.put_annotation("node_name", snapshot["node_name"])
        xray_recorder.put_annotation("pod_name", snapshot["pod_name"])
        xray_recorder.put_annotation("pod_namespace", snapshot["pod_namespace"])
        xray_recorder.put_annotation("host_ip", snapshot["host_ip"])
        xray_recorder.put_annotation("pod_ip", snapshot["pod_ip"])
        xray_recorder.put_annotation("work_seconds", work_seconds)
        xray_recorder.put_metadata("node_snapshot", snapshot, APP_NAME)
        return {
            **snapshot,
            "work_seconds": work_seconds,
        }
    finally:
        xray_recorder.end_segment()
