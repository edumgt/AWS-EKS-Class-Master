# 애플리케이션 배포를 위한 Kubernetes 중요 개념

| 번호  | k8s 개념 이름 |
| ------------- | ------------- |
| 1.  | 시크릿(Secrets)  |
| 2.  | 초기화 컨테이너(Init Containers)  |
| 3.  | Liveness & Readiness 프로브  |
| 4.  | 요청(Requests) & 제한(Limits)  |
| 5.  | 네임스페이스(Namespaces)  |


---

### 둘 다 네임스페이스 단위 정책이지만 목적이 다릅니다.

LimitRange (kind: LimitRange)

개별 Pod/Container/PVC의 최소·최대·기본값을 강제합니다.
예: 컨테이너당 cpu/memory 최소/최대, requests/limits 기본값 자동 주입.
ResourceQuota (kind: ResourceQuota)

네임스페이스 전체 합계 한도를 강제합니다.
예: 전체 requests.cpu, limits.memory, Pod 개수, PVC 개수 상한.
핵심 차이:

범위
LimitRange: 리소스 “1개 객체” 단위
ResourceQuota: 네임스페이스 “총량” 단위
역할
LimitRange: 잘못된 스펙 방지/기본값 제공
ResourceQuota: 팀/네임스페이스 과다 사용 방지

---