# X-Ray Node Analysis Example

이 예제는 `xray-daemon` DaemonSet이 **노드마다 1개씩 실행 중**이라는 점을 이용해서, 애플리케이션 Pod가 **자기 노드의 X-Ray Daemon**으로 트레이스를 보내고 그 트레이스 안에 `nodeName`, `hostIP`, `podName`을 남기도록 구성합니다.

## 핵심 아이디어

- `xray-daemon`은 각 노드에서 `hostPort 2000`으로 수신
- 앱 Pod는 `status.hostIP`를 Downward API로 받아옴
- `AWS_XRAY_DAEMON_ADDRESS=$(HOST_IP):2000` 으로 설정
- `/analyze` 호출 시 X-Ray 세그먼트에 노드 메타데이터 저장

## 추가된 파일

- `node-analysis-example-app/`
- `kube-manifests/03-Node-Analysis-Example/01-node-analysis-deployment.yml`
- `kube-manifests/03-Node-Analysis-Example/02-node-analysis-service.yml`
- `kube-manifests/03-Node-Analysis-Example/03-node-analysis-alb-ingress.yml`
- `kube-manifests/04-Node-Load-Generator/01-node-cpu-loader-daemonset.yml`

## 1. Docker 이미지 빌드 및 푸시

```bash
aws ecr create-repository \
  --repository-name xray-node-analysis-demo \
  --region ap-northeast-2

aws ecr get-login-password --region ap-northeast-2 | \
docker login --username AWS --password-stdin 086015456585.dkr.ecr.ap-northeast-2.amazonaws.com

cd /home/AWS-EKS-Class-Master/13-Microservices-Distributed-Tracing-using-AWS-XRay-on-EKS

docker build -t 086015456585.dkr.ecr.ap-northeast-2.amazonaws.com/xray-node-analysis-demo:latest ./node-analysis-example-app
docker push 086015456585.dkr.ecr.ap-northeast-2.amazonaws.com/xray-node-analysis-demo:latest
```

## 2. 매니페스트 적용

```bash
kubectl apply -f /home/AWS-EKS-Class-Master/13-Microservices-Distributed-Tracing-using-AWS-XRay-on-EKS/kube-manifests/03-Node-Analysis-Example/
kubectl get pods -l app=xray-node-analysis-demo -o wide
kubectl get ingress xray-node-analysis-ingress
```

가능하면 Pod가 서로 다른 노드에 퍼지도록 `podAntiAffinity`를 넣어 두었습니다.

## 3. 테스트

```bash
kubectl get ingress xray-node-analysis-ingress
```

`ADDRESS` 또는 `HOSTS`에 ALB DNS 이름이 보이면 다음처럼 호출합니다.

```bash
curl "http://<ALB-DNS>/analyze?work_seconds=0.3"
```

또는 브라우저에서:

```text
http://<ALB-DNS>/
```

예:

```bash
ALB_DNS=$(kubectl get ingress xray-node-analysis-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "$ALB_DNS"
curl "http://$ALB_DNS/analyze"
```

## 4. 노드 부하 Pod 올리기

각 노드에 CPU 부하를 주는 DaemonSet입니다.

```bash
kubectl apply -f /home/AWS-EKS-Class-Master/13-Microservices-Distributed-Tracing-using-AWS-XRay-on-EKS/kube-manifests/04-Node-Load-Generator/
kubectl get pods -l app=node-cpu-loader -o wide
```

부하를 준 상태에서 ALB로 여러 번 호출합니다.

```bash
for i in $(seq 1 20); do
  curl -s "http://$ALB_DNS/analyze?work_seconds=0.5" >/dev/null
done
```

정리:

```bash
kubectl delete -f /home/AWS-EKS-Class-Master/13-Microservices-Distributed-Tracing-using-AWS-XRay-on-EKS/kube-manifests/04-Node-Load-Generator/
```

## 5. X-Ray에서 확인할 것

- Service name: `xray-node-analysis-demo`
- Annotation:
  - `node_name`
  - `host_ip`
  - `pod_name`
  - `pod_namespace`
  - `pod_ip`
  - `work_seconds`
- Metadata:
  - `node_snapshot`

이 값들을 보면 어떤 요청이 어느 노드의 DaemonSet Pod를 통해 X-Ray로 들어갔는지 확인할 수 있습니다.

CloudWatch의 X-Ray 화면에서는 특히 아래 변화를 보면 좋습니다.

- `xray-node-analysis-demo` 서비스의 평균 응답 시간 증가
- trace 개별 duration 증가
- 같은 `work_seconds`인데도 특정 `node_name`에서 duration이 더 길어지는지 비교

## 6. 예제 해석 포인트

- `HOST_IP`는 앱 Pod가 올라간 **노드 IP**
- `AWS_XRAY_DAEMON_ADDRESS=$(HOST_IP):2000` 는 같은 노드의 X-Ray Daemon으로 보냄
- 여러 Pod를 다른 노드에 분산 배치하면 노드별 트레이스 비교가 쉬워짐
- ALB를 통해 반복 호출하면 요청이 서로 다른 Pod로 분산되면서 노드별 annotation 비교가 쉬워짐
- CPU loader DaemonSet은 노드 자원을 일부 점유해서 trace duration 변화를 더 눈에 띄게 만듦
