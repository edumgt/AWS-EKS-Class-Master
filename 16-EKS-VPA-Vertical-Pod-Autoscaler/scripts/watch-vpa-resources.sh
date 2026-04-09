#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
APP_LABEL="${APP_LABEL:-vpa-nginx}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-vpa-demo-deployment}"
VPA_NAME="${VPA_NAME:-kubengix-vpa}"
SERVICE_NAME="${SERVICE_NAME:-vpa-demo-service-nginx}"
INTERVAL="${INTERVAL:-5}"

while true; do
  clear
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') ===="
  echo
  echo "[Service]"
  kubectl get svc "${SERVICE_NAME}" -n "${NAMESPACE}" \
    -o custom-columns=NAME:.metadata.name,TYPE:.spec.type,EXTERNAL:.status.loadBalancer.ingress[0].hostname,PORT:.spec.ports[0].port \
    --no-headers || true
  echo
  echo "[Deployment]"
  kubectl get deploy "${DEPLOYMENT_NAME}" -n "${NAMESPACE}" \
    -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,DESIRED:.spec.replicas,AVAILABLE:.status.availableReplicas \
    --no-headers || true
  echo
  echo "[Pods]"
  kubectl get pods -n "${NAMESPACE}" -l "app=${APP_LABEL}" \
    -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,AGE:.metadata.creationTimestamp \
    --no-headers || true
  echo
  echo "[Pod Requests/Limits]"
  kubectl get pods -n "${NAMESPACE}" -l "app=${APP_LABEL}" \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{"  requests.cpu="}{.spec.containers[0].resources.requests.cpu}{" requests.memory="}{.spec.containers[0].resources.requests.memory}{"\n"}{"  limits.cpu="}{.spec.containers[0].resources.limits.cpu}{" limits.memory="}{.spec.containers[0].resources.limits.memory}{"\n\n"}{end}' || true
  echo "[VPA Recommendation]"
  kubectl describe vpa "${VPA_NAME}" -n "${NAMESPACE}" 2>/dev/null | sed -n '/Recommendation:/,/Events:/p' || true
  sleep "${INTERVAL}"
done
