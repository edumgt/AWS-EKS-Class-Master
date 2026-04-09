#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
SERVICE_NAME="${SERVICE_NAME:-vpa-demo-service-nginx}"
REQUESTS="${REQUESTS:-200000}"
CONCURRENCY="${CONCURRENCY:-500}"
WORKERS="${WORKERS:-2}"
IMAGE="${IMAGE:-httpd}"

SERVICE_URL="http://${SERVICE_NAME}.${NAMESPACE}.svc.cluster.local/"

echo "Starting VPA load test"
echo "namespace=${NAMESPACE}"
echo "service=${SERVICE_NAME}"
echo "url=${SERVICE_URL}"
echo "requests=${REQUESTS}"
echo "concurrency=${CONCURRENCY}"
echo "workers=${WORKERS}"

for i in $(seq 1 "${WORKERS}"); do
  RUN_NAME="apache-bench-${i}-$(date +%s)"
  echo "Launching worker ${i}: ${RUN_NAME}"
  kubectl run "${RUN_NAME}" \
    --namespace "${NAMESPACE}" \
    --rm -i --tty \
    --restart=Never \
    --image="${IMAGE}" \
    -- \
    ab -n "${REQUESTS}" -c "${CONCURRENCY}" "${SERVICE_URL}" &
done

wait
echo "All load workers completed"
