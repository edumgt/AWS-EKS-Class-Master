# EKS 혼합 모드 배포 - 3개 앱

## 단계-01: 무엇을 학습하나요?
- YAML로 Fargate 프로파일을 작성하고, 한 번에 여러 Fargate 프로파일을 생성하는 방법을 학습합니다.
- `fargate profiles`에서 `namespaces`와 `labels`를 이해합니다.
- 혼합 모드로 3개 앱을 배포합니다.
  - 2개 앱은 서로 다른 2개의 Fargate 프로파일에 배포
  - 1개 앱은 EKS EC2 관리형 노드 그룹에 배포
- 테스트 및 정리

## 단계-02: YAML로 고급 Fargate 프로파일 생성

### Fargate 프로파일 매니페스트 생성
```yml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: eksdemo1  # Name of the EKS Cluster
  region: ap-northeast-2
fargateProfiles:
  - name: fp-app2
    selectors:
      # All workloads in the "ns-app2" Kubernetes namespace will be
      # scheduled onto Fargate:      
      - namespace: ns-app2
  - name: fp-ums
    selectors:
      # All workloads in the "ns-ums" Kubernetes namespace matching the following
      # label selectors will be scheduled onto Fargate:      
      - namespace: ns-ums
        labels:
          runon: fargate     
  
```

## 단계-03: YAML 파일로 Fargate 프로파일 생성
```
# YAML 파일로 Fargate 프로파일 생성
eksctl create fargateprofile -f kube-manifests/01-Fargate-Advanced-Profiles/01-fargate-profiles.yml
```

## 단계-04: Fargate 프로파일 목록 확인
```
# Fargate 프로파일 목록
eksctl get fargateprofile --cluster eksdemo1

# YAML 형식으로 보기
eksctl get fargateprofile --cluster eksdemo1 -o yaml
```

## 단계-05: App1, App2, UMS 매니페스트 검토
- 네임스페이스 검토
  - ns-app1
  - ns-app2
  - ns-ums
- `ns-ums` 네임스페이스에 있는 레이블 논의
```yml
      - namespace: ns-ums
        labels:
          runon: fargate     
   
```
- target-type 논의
```yml
    # For Fargate
    alb.ingress.kubernetes.io/target-type: ip    
```

## 단계-06: 앱 배포
- **사전 점검:** UMS 서비스에 필요한 RDS DB가 정상 실행 중인지 확인합니다.
```
# 앱 배포
kubectl apply -R -f kube-manifests/02-Applications/
```

## 단계-07: 배포된 앱 확인

### kubectl로 확인
```
# Ingress 확인
kubectl get ingress --all-namespaces

# 파드 확인
kubectl get pods --all-namespaces -o wide

# Fargate 노드 확인
kubectl get nodes -o wide
```

### ALB 및 Target Groups 확인
- ALB 리스너, 규칙 확인
- Target Groups 확인
  - App1: Target Type이 `instance`여야 함
  - App2, UMS: Target Type이 `ip`여야 함


### 애플리케이션 접속
- App1: http://app1.kubeoncloud.com/app1/index.html
- App2: http://app2.kubeoncloud.com/app2/index.html
- UMS Health Status Page: http://ums.kubeoncloud.com/usermgmt/health-status
- UMS List Users: http://ums.kubeoncloud.com/usermgmt/users 


## 단계-08: 앱 삭제
```
# 앱 삭제
kubectl delete -R -f kube-manifests/02-Applications/
```

## 단계-09: Fargate 프로파일 삭제
```
# 클러스터의 Fargate 프로파일 목록 확인
eksctl get fargateprofile --cluster eksdemo1

# Fargate 프로파일 삭제
eksctl delete fargateprofile --cluster <cluster-name> --name <Fargate-Profile-Name> --wait
eksctl delete fargateprofile --cluster eksdemo1 --name fp-app2 --wait
eksctl delete fargateprofile --cluster eksdemo1 --name fp-ums --wait

```

## 교차 네임스페이스 ALB Ingress 관련 GitHub 이슈 참고
- https://github.com/kubernetes/kubernetes/issues/17088
