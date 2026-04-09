# EKS 모니터링 - CloudWatch Container Insights + Prometheus + Grafana

## Step-01: 소개
- 이 디렉터리는 이제 `CloudWatch Container Insights` 실습만이 아니라, `Prometheus + Grafana`를 함께 붙여 `eksdemo1`의 node / pod 메트릭을 시각화하는 실습까지 포함합니다.
- 현재 `kube-manifests`에는 아래 두 흐름이 함께 들어 있습니다.
  - CloudWatch Container Insights용 샘플 앱
  - Prometheus / Grafana / node-exporter / kube-state-metrics / CPU load DaemonSet
  - CloudWatch 샘플 앱 부하 생성용 Deployment

## Step-02: EKS 워커 노드 역할에 CloudWatch 정책 연결
- Services -> EC2 -> Worker Node EC2 Instance -> IAM Role -> 해당 역할 클릭
```
# Sample Role ARN
arn:aws:iam::180789647333:role/eksctl-eksdemo1-nodegroup-eksdemo-NodeInstanceRole-1FVWZ2H3TMQ2M

# 연결할 정책
Associate Policy: CloudWatchAgentServerPolicy
```

## Step-03: Container Insights 설치

### CloudWatch Agent와 Fluentd를 DaemonSet으로 배포
- 이 명령은 다음을 수행합니다.
  - Namespace `amazon-cloudwatch` 생성
  - 두 DaemonSet에 필요한 보안 객체 생성:
    - SecurityAccount
    - ClusterRole
    - ClusterRoleBinding
  - 메트릭을 CloudWatch로 전송하는 `Cloudwatch-Agent` DaemonSet 배포
  - 로그를 CloudWatch로 전송하는 Fluentd DaemonSet 배포
  - 두 DaemonSet의 ConfigMap 구성 배포
```
# 템플릿
curl -s https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml | sed "s/{{cluster_name}}/<REPLACE_CLUSTER_NAME>/;s/{{region_name}}/<REPLACE-AWS_REGION>/" | kubectl apply -f -

# 클러스터 이름과 리전 교체
curl -s https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml | sed "s/{{cluster_name}}/eksdemo1/;s/{{region_name}}/ap-northeast-2/" | kubectl apply -f -
```

## 확인
```
# DaemonSets 목록
kubectl -n amazon-cloudwatch get daemonsets
```


## Step-04: 샘플 Nginx 애플리케이션 배포
- 현재 `Sample-Nginx-App.yml`은 단순 Pod 1개가 아니라, CloudWatch 실습에 맞게 아래를 포함하도록 보강돼 있습니다.
  - `cloudwatch-demo` 네임스페이스
  - NGINX ConfigMap
  - `sample-nginx-deployment` 2 replicas
  - `sample-nginx-service` ClusterIP Service
  - readiness / liveness probe
  - access log / error log가 남는 기본 NGINX 설정

```
# 배포
kubectl apply -f kube-manifests/Sample-Nginx-App.yml

# 확인
kubectl get all -n cloudwatch-demo
```

## Step-05: 샘플 Nginx 애플리케이션에 부하 생성
- 부하도 이제 로컬 YAML로 재현 가능하게 추가했습니다.
- `16-cloudwatch-load-generator.yml` 은 `sample-nginx-service` 로 지속적으로 요청을 보내 access log와 container metrics가 꾸준히 쌓이도록 합니다.

```bash
kubectl apply -f kube-manifests/16-cloudwatch-load-generator.yml
kubectl get pods -n cloudwatch-demo
```

- 기존처럼 일회성 `ab` 테스트를 직접 실행해도 됩니다.

```
# 부하 생성
kubectl run apache-bench --rm -it --restart=Never --image=httpd \
  -n cloudwatch-demo -- \
  ab -n 500000 -c 1000 http://sample-nginx-service.cloudwatch-demo.svc.cluster.local/
```

## Step-06: CloudWatch 대시보드 접속
- CloudWatch Container Insights 대시보드에 접속


## Step-07: CloudWatch Log Insights
- 컨테이너 로그 확인
- 컨테이너 성능 로그 확인

## Step-08: Container Insights - Log Insights 심화
- 로그 그룹
- Log Insights
- 대시보드 생성

### 평균 노드 CPU 사용률 그래프 만들기
- DashBoard Name: EKS-Performance
- Widget Type: Bar
- Log Group: /aws/containerinsights/eksdemo1/performance
```
STATS avg(node_cpu_utilization) as avg_node_cpu_utilization by NodeName
| SORT avg_node_cpu_utilization DESC 
```

### 컨테이너 재시작
- DashBoard Name: EKS-Performance
- Widget Type: Table
- Log Group: /aws/containerinsights/eksdemo1/performance
```
STATS avg(number_of_container_restarts) as avg_number_of_container_restarts by PodName
| SORT avg_number_of_container_restarts DESC
```

### 클러스터 노드 장애
- DashBoard Name: EKS-Performance
- Widget Type: Table
- Log Group: /aws/containerinsights/eksdemo1/performance
```
stats avg(cluster_failed_node_count) as CountOfNodeFailures 
| filter Type="Cluster" 
| sort @timestamp desc
```
### 컨테이너별 CPU 사용량
- DashBoard Name: EKS-Performance
- Widget Type: Bar
- Log Group: /aws/containerinsights/eksdemo1/performance
```
stats pct(container_cpu_usage_total, 50) as CPUPercMedian by kubernetes.container_name 
| filter Type="Container"
```

### 요청된 Pod vs 실행 중인 Pod
- DashBoard Name: EKS-Performance
- Widget Type: Bar
- Log Group: /aws/containerinsights/eksdemo1/performance
```
fields @timestamp, @message 
| sort @timestamp desc 
| filter Type="Pod" 
| stats min(pod_number_of_containers) as requested, min(pod_number_of_running_containers) as running, ceil(avg(pod_number_of_containers-pod_number_of_running_containers)) as pods_missing by kubernetes.pod_name 
| sort pods_missing desc
```

### 컨테이너 이름별 애플리케이션 로그 에러
- DashBoard Name: EKS-Performance
- Widget Type: Bar
- Log Group: /aws/containerinsights/eksdemo1/application
```
stats count() as countoferrors by kubernetes.container_name 
| filter stream="stderr" 
| sort countoferrors desc
```

- **참고**: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-view-metrics.html


## Step-09: Container Insights - CloudWatch 알람
### 알람 생성 - 노드 CPU 사용률
- **메트릭 및 조건 지정**
  - **Select Metric:** Container Insights -> ClusterName -> node_cpu_utilization
  - **Metric Name:** eksdemo1_node_cpu_utilization
  - **Threshold Value:** 4 
  - **중요:** 4% 이상의 CPU 사용률에서 알림 이메일 발송 (테스트용) 
- **액션 구성**
  - **새 주제 생성:** eks-alerts
  - **Email:** dkalyanreddy@gmail.com
  - **Create Topic** 클릭
  - **중요:** 이메일 구독 확인이 필요합니다.
- **이름 및 설명 추가**
  - **Name:** EKS-Nodes-CPU-Alert
  - **Description:** EKS Nodes CPU alert notification  
  - Next 클릭
- **Preview**
  - Preview and Create Alarm
- **사용자 대시보드에 알람 추가**
- 부하 생성 및 알람 확인
```
# 부하 생성
kubectl run --generator=run-pod/v1 apache-bench -i --tty --rm --image=httpd -- ab -n 500000 -c 1000 http://sample-nginx-service.default.svc.cluster.local/ 
```

## Step-10: Container Insights 정리
```
# 템플릿
curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml | sed "s/{{cluster_name}}/cluster-name/;s/{{region_name}}/cluster-region/" | kubectl delete -f -

# 클러스터 이름 & 리전 교체
curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml | sed "s/{{cluster_name}}/eksdemo1/;s/{{region_name}}/ap-northeast-2/" | kubectl delete -f -
```

```bash
kubectl delete -f kube-manifests/16-cloudwatch-load-generator.yml
kubectl delete -f kube-manifests/Sample-Nginx-App.yml
```

## Step-11: Prometheus + Grafana로 EKS Node / Pod 메트릭 시각화 추가
- CloudWatch Container Insights는 그대로 유지하고, 별도로 `Prometheus + Grafana`를 `monitoring` 네임스페이스에 올립니다.
- 이 구성은 현재 `eksdemo1`의 node, pod, Jupyter autoscaling Pod 상태를 Grafana 대시보드로 시각화합니다.
- 포함된 컴포넌트
  - `kube-state-metrics`
  - `node-exporter`
  - `prometheus-server`
  - `grafana`
  - `node-cpu-load` (강제 CPU 스파이크 확인용)

### 배포 파일
```bash
kubectl apply -f kube-manifests/10-monitoring-namespace.yml
kubectl apply -f kube-manifests/11-kube-state-metrics.yml
kubectl apply -f kube-manifests/12-node-exporter.yml
kubectl apply -f kube-manifests/13-prometheus.yml
kubectl apply -f kube-manifests/14-grafana.yml
```

### 배포 상태 확인
```bash
kubectl get pods -n monitoring
kubectl get svc -n monitoring
```

### Grafana 접속 주소 확인
```bash
kubectl get svc grafana -n monitoring
kubectl get svc grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### Grafana 기본 계정
- ID: `admin`
- Password: `admin1234`

### 기본 제공 대시보드
- `EKS Node and Pod Overview`
  - Node CPU Usage
  - Node Memory Usage
  - Pod Phase Count
  - Top Pod CPU Usage
  - Top Pod Memory Usage
- `EKS Jupyter Autoscaling`
  - `ca-jupyter-notebook` Pod의 Running / Pending 수
  - Jupyter Pod별 CPU 사용량
  - Jupyter Pod별 메모리 사용량

### Prometheus 확인
```bash
kubectl port-forward -n monitoring svc/prometheus-server 9090:9090
```

- 브라우저에서 `http://localhost:9090`
- 예시 PromQL
```promql
100 * avg by (instance) (1 - rate(node_cpu_seconds_total{mode="idle"}[5m]))
```

```promql
topk(10, sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m])))
```

```promql
topk(10, sum by (namespace, pod) (container_memory_working_set_bytes{container!="",image!=""}))
```

### 실습 팁
- `17-EKS-Autoscaling-Cluster-Autoscaler`에서 만든 `ca-jupyter-notebook` 8개 Pod가 떠 있는 상태면 Grafana에서 autoscaling 결과를 바로 볼 수 있습니다.
- 노드가 늘어나는 과정은 `Node CPU Usage`, `Pod Phase Count`, `EKS Jupyter Autoscaling` 대시보드에서 확인하기 좋습니다.

## Step-12: Node CPU 시계열 강제 부하 실습
- `15-node-cpu-load-daemonset.yml` 은 각 노드마다 CPU burner Pod를 1개씩 띄워 `Node CPU Usage` 그래프가 급격히 상승하는 모습을 확인하기 위한 실습용 매니페스트입니다.

```bash
kubectl apply -f kube-manifests/15-node-cpu-load-daemonset.yml
kubectl get pods -n monitoring -l app=node-cpu-load -o wide
kubectl top nodes
```

- Grafana에서 `EKS Node and Pod Overview` 대시보드의 `Node CPU Usage` 패널을 보면 배포 시점부터 CPU 시계열이 급상승해야 정상입니다.

부하 종료:

```bash
kubectl delete -f kube-manifests/15-node-cpu-load-daemonset.yml
```

## Step-13: Prometheus / Grafana 정리
```bash
kubectl delete -f kube-manifests/14-grafana.yml
kubectl delete -f kube-manifests/13-prometheus.yml
kubectl delete -f kube-manifests/12-node-exporter.yml
kubectl delete -f kube-manifests/11-kube-state-metrics.yml
kubectl delete -f kube-manifests/10-monitoring-namespace.yml
```

## Step-14: 애플리케이션 정리
```
# 앱 삭제
kubectl delete -f  kube-manifests/
```

## 참고 자료
- https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/deploy-container-insights-EKS.html
- https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights-Prometheus-Setup.html
- https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-reference-performance-entries-EKS.html
