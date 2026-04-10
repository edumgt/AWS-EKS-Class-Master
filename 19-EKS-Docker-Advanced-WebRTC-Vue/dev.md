# CloudWatch JSON Log Integration Guide for FE Developers

이 문서는 `New Relic`, `Grafana` 같은 별도 관측 UI 없이, `CloudWatch Logs` 데이터를 JSON으로 받아서 Vue 프런트에서 `ApexCharts` 같은 차트 라이브러리로 붙이는 방법을 설명합니다.

목표:
- 애플리케이션 로그를 CloudWatch에 적재
- 서버 API에서 CloudWatch Logs Insights 쿼리 실행
- FE 개발자는 JSON API만 호출
- Vue/ApexCharts에서 시계열 차트 렌더링

---

## 1. 전체 구조

권장 구조는 아래와 같습니다.

1. `frontend`, `signaling` 컨테이너가 JSON 로그를 `stdout/stderr` 로 출력
2. EKS `Container Insights` 또는 `CloudWatch Agent + Fluent Bit` 가 로그를 CloudWatch Logs로 전송
3. 백엔드 API가 `CloudWatch Logs Insights` 쿼리를 실행
4. API가 차트에 적합한 JSON 포맷으로 변환
5. Vue FE가 이 JSON을 호출해 `ApexCharts` 로 렌더링

즉, 브라우저가 CloudWatch에 직접 붙지 않고:

`CloudWatch Logs -> Backend API -> JSON -> Vue/ApexCharts`

형태로 가는 것이 가장 안전합니다.

---

## 2. 왜 CloudWatch 직접 호출이 아니라 API 중간 계층이 필요한가

브라우저에서 CloudWatch를 직접 호출하는 방식은 권장하지 않습니다.

이유:
- IAM 자격 증명 노출 위험
- CORS 및 인증 처리 복잡
- FE에 AWS SDK/권한 정책을 강하게 노출하게 됨
- 쿼리 결과를 프런트가 직접 가공해야 해서 재사용성이 떨어짐

권장 방식:
- 서버가 AWS IAM Role 또는 자격 증명으로 CloudWatch 조회
- FE에는 정제된 JSON만 반환

---

## 3. CloudWatch 에 저장될 로그 전제

가능하면 애플리케이션 로그는 JSON 한 줄 로그로 남기는 것이 좋습니다.

예:

```json
{"timestamp":"2026-04-10T10:00:00Z","level":"info","service":"frontend","event":"room_join_click","roomId":"11111","userId":"u-001"}
{"timestamp":"2026-04-10T10:00:02Z","level":"error","service":"signaling","event":"websocket_connect_failed","roomId":"11111","reason":"timeout"}
```

이렇게 남기면 CloudWatch Logs Insights에서 필드 기반 집계가 쉬워집니다.

실습 기준 기본 로그 그룹:

```text
/aws/containerinsights/<CLUSTER_NAME>/application
```

예:

```text
/aws/containerinsights/eksdemo2/application
```

---

## 4. FE 개발자가 기대하면 좋은 JSON 응답 포맷

FE 입장에서는 CloudWatch 원본 형식보다 아래처럼 차트에 바로 넣을 수 있는 응답이 좋습니다.

예시:

```json
{
  "rangeMinutes": 60,
  "binMinutes": 5,
  "series": [
    {
      "name": "frontend_errors",
      "data": [
        ["2026-04-10T10:00:00Z", 3],
        ["2026-04-10T10:05:00Z", 1],
        ["2026-04-10T10:10:00Z", 7]
      ]
    },
    {
      "name": "signaling_errors",
      "data": [
        ["2026-04-10T10:00:00Z", 0],
        ["2026-04-10T10:05:00Z", 2],
        ["2026-04-10T10:10:00Z", 1]
      ]
    }
  ],
  "recentLogs": [
    {
      "timestamp": "2026-04-10T10:12:10Z",
      "service": "signaling",
      "level": "error",
      "event": "websocket_connect_failed",
      "message": "timeout"
    }
  ]
}
```

이 포맷이면 FE 개발자는 변환 없이 거의 바로 차트에 연결할 수 있습니다.

---

## 5. CloudWatch Logs Insights 쿼리 예시

### 5-1. 에러 로그 볼륨 시계열

```sql
fields @timestamp, kubernetes.container_name, @message
| filter kubernetes.namespace_name = "webrtc"
| filter kubernetes.container_name in ["frontend","signaling"]
| filter @message like /ERROR|Error|error|Exception|exception|failed|Failed|timeout|Timeout/
| stats count(*) as value by bin(5m), kubernetes.container_name
| sort bin(5m) asc
```

### 5-2. 전체 로그 볼륨 시계열

```sql
fields @timestamp, kubernetes.container_name
| filter kubernetes.namespace_name = "webrtc"
| filter kubernetes.container_name in ["frontend","signaling"]
| stats count(*) as value by bin(5m), kubernetes.container_name
| sort bin(5m) asc
```

### 5-3. 최근 로그 20건

```sql
fields @timestamp, @message, kubernetes.container_name, kubernetes.pod_name
| filter kubernetes.namespace_name = "webrtc"
| filter kubernetes.container_name in ["frontend","signaling"]
| sort @timestamp desc
| limit 20
```

---

## 6. 백엔드 API 설계 예시

권장 엔드포인트:

- `GET /api/log-timeseries?rangeMinutes=60&binMinutes=5`
- `GET /api/log-recent?limit=20`

예상 동작:
- 서버가 CloudWatch Logs Insights 쿼리 실행
- 결과를 `ApexCharts` 친화적 JSON으로 변환
- FE는 그 JSON만 사용

예시 Node pseudo-code:

```js
import {
  CloudWatchLogsClient,
  StartQueryCommand,
  GetQueryResultsCommand
} from "@aws-sdk/client-cloudwatch-logs"

const client = new CloudWatchLogsClient({ region: "ap-northeast-2" })

async function runQuery(logGroupName, queryString, startTime, endTime) {
  const start = await client.send(
    new StartQueryCommand({
      logGroupName,
      startTime,
      endTime,
      queryString
    })
  )

  const queryId = start.queryId

  for (let i = 0; i < 20; i += 1) {
    const result = await client.send(
      new GetQueryResultsCommand({ queryId })
    )

    if (result.status === "Complete") {
      return result.results || []
    }

    await new Promise((resolve) => setTimeout(resolve, 1000))
  }

  throw new Error("CloudWatch query timeout")
}
```

---

## 7. ApexCharts 연결 예시

FE 개발자는 아래 형태로 연결하면 됩니다.

### 7-1. API 호출 예시

```js
const response = await fetch("/api/log-timeseries?rangeMinutes=60&binMinutes=5")
const payload = await response.json()
```

### 7-2. ApexCharts series 예시

```js
const chartSeries = payload.series.map((item) => ({
  name: item.name,
  data: item.data.map(([timestamp, value]) => ({
    x: new Date(timestamp).getTime(),
    y: value
  }))
}))
```

### 7-3. Vue 컴포넌트 예시

```vue
<script setup>
import { onMounted, ref } from "vue"

const series = ref([])

onMounted(async () => {
  const response = await fetch("/api/log-timeseries?rangeMinutes=60&binMinutes=5")
  const payload = await response.json()

  series.value = payload.series.map((item) => ({
    name: item.name,
    data: item.data.map(([timestamp, value]) => ({
      x: new Date(timestamp).getTime(),
      y: value
    }))
  }))
})

const chartOptions = {
  chart: {
    type: "line",
    height: 320,
    toolbar: { show: true }
  },
  xaxis: {
    type: "datetime"
  },
  stroke: {
    curve: "smooth",
    width: 3
  },
  dataLabels: {
    enabled: false
  },
  yaxis: {
    min: 0
  }
}
</script>
```

---

## 8. IAM 권한

백엔드 API가 CloudWatch를 조회하려면 최소 아래 권한이 필요합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:StartQuery",
        "logs:GetQueryResults",
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

권장:
- IRSA 또는 Pod Role 사용
- 프런트 브라우저에 AWS 자격 증명 노출 금지

---

## 9. 운영 팁

- 차트 조회 bin은 `1m`, `5m`, `15m` 정도로 제한하는 것이 좋습니다.
- Logs Insights 쿼리는 비용이 발생할 수 있으므로, FE 자동 polling 주기를 너무 짧게 두지 않는 것이 좋습니다.
- 일반적으로 `30초~60초` 이상 polling 권장
- 실시간이 매우 중요하면 별도 로그 파이프라인이나 캐시 계층을 고려하세요.

---

## 10. 추천 결론

이번 요구사항에는 아래 방식이 가장 적합합니다.

- 수집: CloudWatch Logs / Container Insights
- 조회: 백엔드 API
- 포맷: FE 친화 JSON
- 시각화: Vue + ApexCharts

즉, FE 개발자는 CloudWatch 자체를 알 필요 없이:

1. `/api/log-timeseries`
2. `/api/log-recent`

이 두 종류의 JSON만 받으면 충분합니다.

---

## 11. 이 실습 기준 권장 엔드포인트

`webrtc` 네임스페이스 기준으로는 아래 응답을 준비해두면 좋습니다.

- `GET /api/log-timeseries?rangeMinutes=60&binMinutes=5`
  - `frontend`, `signaling` 로그 건수
  - 에러 로그 건수
- `GET /api/log-recent?limit=20`
  - 최근 로그 목록
- `GET /api/observability/timeseries`
  - 로그 + 메트릭 묶음형 응답이 필요할 때 사용

필요 시 FE는 이 JSON을 그대로 ApexCharts, ECharts, Chart.js 어느 쪽에도 연결할 수 있습니다.
