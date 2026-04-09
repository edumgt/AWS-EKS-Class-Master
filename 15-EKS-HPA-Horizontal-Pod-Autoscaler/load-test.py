#!/usr/bin/env python3
"""
부하 테스트 스크립트
FastAPI 백엔드에 대량의 요청을 보내 HPA를 트리거합니다
"""
import requests
import concurrent.futures
import time
import sys
from typing import List

# 백엔드 서비스 URL (LoadBalancer URL로 변경)
BACKEND_URL = "http://localhost:8000"  # 또는 실제 LoadBalancer URL

def create_jupyter_session(user_id: int) -> dict:
    """Jupyter Lab 세션 생성"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/session/create",
            json={"username": f"user{user_id}"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "user_id": user_id}

def generate_cpu_load() -> dict:
    """CPU 부하 생성"""
    try:
        response = requests.post(f"{BACKEND_URL}/load/generate", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_metrics() -> dict:
    """현재 메트릭 조회"""
    try:
        response = requests.get(f"{BACKEND_URL}/metrics", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def load_test_sessions(num_users: int = 20):
    """여러 사용자 세션 동시 생성"""
    print(f"=== Jupyter Lab 세션 생성 부하 테스트 ===")
    print(f"생성할 사용자 수: {num_users}")
    
    start_time = time.time()
    
    # 병렬로 세션 생성
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_jupyter_session, i) for i in range(num_users)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    elapsed_time = time.time() - start_time
    
    # 결과 분석
    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    
    print(f"\n결과:")
    print(f"  성공: {len(successful)}")
    print(f"  실패: {len(failed)}")
    print(f"  총 소요 시간: {elapsed_time:.2f}초")
    
    if failed:
        print(f"\n실패한 요청:")
        for fail in failed[:5]:  # 처음 5개만 표시
            print(f"  - {fail}")
    
    return successful

def load_test_cpu(num_requests: int = 100, workers: int = 10):
    """CPU 부하 테스트"""
    print(f"\n=== CPU 부하 생성 테스트 ===")
    print(f"요청 수: {num_requests}, 동시 워커: {workers}")
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(generate_cpu_load) for _ in range(num_requests)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    elapsed_time = time.time() - start_time
    
    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    
    print(f"\n결과:")
    print(f"  성공: {len(successful)}")
    print(f"  실패: {len(failed)}")
    print(f"  총 소요 시간: {elapsed_time:.2f}초")
    print(f"  초당 요청 수: {num_requests/elapsed_time:.2f} req/s")

def monitor_metrics(duration: int = 60, interval: int = 5):
    """메트릭 모니터링"""
    print(f"\n=== 메트릭 모니터링 ({duration}초) ===")
    
    end_time = time.time() + duration
    
    while time.time() < end_time:
        metrics = get_metrics()
        print(f"[{time.strftime('%H:%M:%S')}] 활성 세션: {metrics.get('active_sessions', 'N/A')}")
        time.sleep(interval)

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print(f"  {sys.argv[0]} <command> [options]")
        print("\nCommands:")
        print("  sessions <N>    - N명의 사용자 세션 생성 (기본값: 20)")
        print("  cpu <N> <W>     - N개의 CPU 부하 요청, W개 워커 (기본값: 100, 10)")
        print("  monitor <D>     - D초 동안 메트릭 모니터링 (기본값: 60)")
        print("  all             - 전체 부하 테스트 실행")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # 백엔드 URL 설정 (환경 변수 또는 인자)
    global BACKEND_URL
    if len(sys.argv) > 2 and sys.argv[2].startswith("http"):
        BACKEND_URL = sys.argv[2]
        print(f"백엔드 URL: {BACKEND_URL}\n")
    
    try:
        if command == "sessions":
            num_users = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            load_test_sessions(num_users)
        
        elif command == "cpu":
            num_requests = int(sys.argv[3]) if len(sys.argv) > 3 else 100
            workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
            load_test_cpu(num_requests, workers)
        
        elif command == "monitor":
            duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
            monitor_metrics(duration)
        
        elif command == "all":
            print("전체 부하 테스트 시작...\n")
            
            # 1. 초기 메트릭 확인
            print("초기 상태:")
            print(get_metrics())
            
            # 2. 세션 생성 테스트
            sessions = load_test_sessions(15)
            time.sleep(5)
            
            # 3. CPU 부하 테스트
            load_test_cpu(50, 5)
            time.sleep(5)
            
            # 4. 메트릭 모니터링
            monitor_metrics(30, 5)
            
            print("\n전체 테스트 완료!")
        
        else:
            print(f"알 수 없는 명령: {command}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
