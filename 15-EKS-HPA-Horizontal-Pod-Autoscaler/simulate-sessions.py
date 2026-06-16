#!/usr/bin/env python3
"""
가상 세션 시뮬레이터
- 20개 가상 사용자 생성 및 로그인
- 10개 Jupyter Pod 세션 실행
- HPA 트리거를 위한 CPU 부하 생성
"""
import requests
import concurrent.futures
import time
import uuid
import json
from datetime import datetime

BASE_URL = "http://k8s-default-jupyterm-e6288c70b5-6b61d19543e9f3fd.elb.ap-northeast-2.amazonaws.com"
PASSWORD = "123456"

# 20개 가상 사용자
VIRTUAL_USERS = [f"vuser{i:02d}" for i in range(1, 21)]
# 10명만 실제 Pod 실행
ACTIVE_USERS = VIRTUAL_USERS[:10]


def login(username: str) -> dict:
    """사용자 로그인 → Bearer 토큰 발급"""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "password": PASSWORD},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "username": username,
                "token": data["access_token"],
                "role": data["role"],
                "ok": True
            }
        return {"username": username, "ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"username": username, "ok": False, "error": str(e)}


def create_session(username: str, token: str) -> dict:
    """Jupyter Pod 세션 생성"""
    try:
        resp = requests.post(
            f"{BASE_URL}/users/{username}/session",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "username": username,
                "session_id": data.get("session_id"),
                "status": data.get("status"),
                "can_launch": data.get("can_launch"),
                "queue_position": data.get("queue_position"),
                "launch_url": data.get("launch_url"),
                "ok": True
            }
        return {"username": username, "ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"username": username, "ok": False, "error": str(e)}


def get_session_status(session_id: str, token: str) -> dict:
    """세션 상태 조회"""
    try:
        resp = requests.get(
            f"{BASE_URL}/session/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def generate_cpu_load() -> dict:
    """HPA 트리거용 CPU 부하"""
    try:
        resp = requests.post(f"{BASE_URL}/load/generate", timeout=60)
        return resp.json() if resp.status_code == 200 else {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def print_separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    print_separator("1단계: 가상 사용자 20명 생성 및 로그인")
    print(f"대상 사용자: {', '.join(VIRTUAL_USERS)}\n")

    login_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(login, u): u for u in VIRTUAL_USERS}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            login_results[result["username"]] = result
            status = "✓" if result["ok"] else "✗"
            token_preview = result.get("token", "")[:12] + "..." if result.get("token") else "-"
            print(f"  [{status}] {result['username']:10s}  token={token_preview}  role={result.get('role','-')}")

    ok_logins = {u: r for u, r in login_results.items() if r["ok"]}
    print(f"\n로그인 성공: {len(ok_logins)}/20")

    print_separator("2단계: 10개 Jupyter Pod 세션 생성")
    print(f"실행 대상: {', '.join(ACTIVE_USERS)}\n")

    session_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for u in ACTIVE_USERS:
            if u in ok_logins:
                f = executor.submit(create_session, u, ok_logins[u]["token"])
                futures[f] = u

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            session_results[result["username"]] = result
            if result["ok"]:
                print(f"  [✓] {result['username']:10s}  session={result['session_id']}  "
                      f"status={result['status']}  queue_pos={result.get('queue_position')}")
            else:
                print(f"  [✗] {result['username']:10s}  error={result['error']}")

    ok_sessions = {u: r for u, r in session_results.items() if r.get("ok")}
    print(f"\n세션 생성 성공: {len(ok_sessions)}/10")

    print_separator("3단계: HPA 트리거 — CPU 부하 생성")
    print("20개의 CPU 집약적 요청을 병렬 전송...\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_cpu_load) for _ in range(20)]
        load_results = [f.result() for f in concurrent.futures.as_completed(futures)]

    load_ok = sum(1 for r in load_results if "error" not in r)
    print(f"CPU 부하 요청 성공: {load_ok}/20")

    print_separator("4단계: 세션 상태 모니터링 (30초)")
    print("5초 간격으로 세션 상태 확인...\n")

    for tick in range(6):
        ts = datetime.now().strftime("%H:%M:%S")
        running = queued = creating = 0
        for u, sess in ok_sessions.items():
            token = ok_logins[u]["token"]
            st = get_session_status(sess["session_id"], token)
            s = st.get("status", "?")
            if s == "running":
                running += 1
            elif s == "queued":
                queued += 1
            elif s == "creating":
                creating += 1
        print(f"  [{ts}] running={running}  creating={creating}  queued={queued}")
        if tick < 5:
            time.sleep(5)

    print_separator("결과 요약")
    print(f"  가상 사용자 생성:  20명")
    print(f"  로그인 성공:       {len(ok_logins)}/20")
    print(f"  Jupyter Pod 세션:  {len(ok_sessions)}/10")
    print(f"  CPU 부하 요청:     {load_ok}/20")
    print(f"\n  HPA 확인 명령:")
    print(f"  kubectl get hpa jupyter-manager-hpa -w")
    print(f"\n  Pod 현황 확인:")
    print(f"  kubectl get pods -l app=jupyter-lab")
    print(f"\n  세션 목록 (Admin):")
    print(f"  curl -s {BASE_URL}/sessions -H 'Authorization: Bearer <admin_token>' | python3 -m json.tool")


if __name__ == "__main__":
    main()
