# AWS EKS - Fargate 프로파일

1. Fargate 프로파일 - 기본
2. YAML을 사용한 고급 Fargate 프로파일

## 참고 자료
- https://eksctl.io/usage/fargate-support/
- https://docs.aws.amazon.com/eks/latest/userguide/fargate.html
- https://kubernetes-sigs.github.io/aws-alb-ingress-controller/guide/ingress/annotation/#target-type


### Fargate 설명

AWS Fargate는 서버를 직접 만들고 관리하지 않고도 컨테이너를 실행할 수 있게 해주는 AWS의 서버리스 컴퓨팅 방식입니다.

EKS 기준으로 보면, 원래는 우리가 EC2 노드를 만들고 그 위에 Pod를 올립니다.
그런데 Fargate를 쓰면 EC2 노드 관리 없이 AWS가 Pod를 실행할 컴퓨팅 리소스를 대신 준비해줍니다.

쉽게 비교하면:

EC2 worker node
우리가 노드 생성/패치/스케일 관리
Pod는 그 노드 위에서 실행
Fargate
노드 관리 없음
지정한 Pod를 AWS가 알아서 실행
EKS에서의 핵심 개념:

Fargate는 "클러스터 전체를 다 서버리스로 바꾸는 것"이라기보다
Fargate Profile에 매칭되는 Pod만 Fargate에서 실행되게 하는 방식입니다.
즉:

EKS 클러스터 생성
Fargate Profile 생성
특정 namespace 또는 label selector에 맞는 Pod 정의
그 Pod들이 EC2 노드 대신 Fargate에서 실행
예를 들면:

namespace: fp-default
이 namespace의 Pod는 Fargate에서 실행
나머지 Pod는 EC2 node group에서 실행
장점:

노드 서버 관리가 거의 필요 없음
소규모/간헐적 워크로드에 편리
보안 격리가 단순해지는 경우가 있음
운영 부담 감소
단점/제약:

DaemonSet 같은 워크로드 제약이 있음
Node에 직접 접근하는 형태의 운영이 어려움
일부 네트워킹/스토리지/에이전트 패턴은 EC2 기반보다 제한적
비용 구조상 항상 더 싼 것은 아님
언제 쓰면 좋은가:

운영 복잡도를 줄이고 싶을 때
간단한 웹앱, 배치, API 워크로드
노드 관리보다 애플리케이션 배포에 집중하고 싶을 때
언제 EC2가 더 나을 수 있나:

DaemonSet 많이 필요
GPU/특수 인스턴스 필요
노드 레벨 튜닝 필요
대규모 장시간 워크로드로 비용 최적화가 중요
한 줄 정리:

EKS on EC2 = "내가 노드를 운영"
EKS on Fargate = "Pod 실행 인프라를 AWS가 대신 운영"