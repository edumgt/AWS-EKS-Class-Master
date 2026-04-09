#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
SERVICE_NAME="${SERVICE_NAME:-nginx-canary-clb-service}"
APP_LABEL="${APP_LABEL:-nginx-canary-demo}"
FROM_VERSION="${FROM_VERSION:-stable}"
TO_VERSION="${TO_VERSION:-canary}"
THRESHOLD="${THRESHOLD:-10}"
REQUEST_COUNT="${REQUEST_COUNT:-12}"
VERIFY_COUNT="${VERIFY_COUNT:-3}"
SLEEP_SECONDS="${SLEEP_SECONDS:-0.2}"

log() {
  printf '[demo] %s\n' "$1"
}

require_kubectl() {
  if ! command -v kubectl >/dev/null 2>&1; then
    echo "kubectl is required" >&2
    exit 1
  fi
}

patch_service_version() {
  local version="$1"
  kubectl patch svc "${SERVICE_NAME}" -n "${NAMESPACE}" --type merge \
    -p "{\"spec\":{\"selector\":{\"app\":\"${APP_LABEL}\",\"version\":\"${version}\"}}}" >/dev/null
}

count_requests_for_version() {
  local version="$1"
  local total=0
  local pods

  pods="$(kubectl get pods -n "${NAMESPACE}" -l "app=${APP_LABEL},version=${version}" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')"

  if [[ -z "${pods}" ]]; then
    echo 0
    return
  fi

  while IFS= read -r pod; do
    [[ -z "${pod}" ]] && continue
    local count
    count="$(kubectl logs -n "${NAMESPACE}" "${pod}" 2>/dev/null | grep -c '"GET / HTTP/1.1"' || true)"
    total=$((total + count))
  done <<< "${pods}"

  echo "${total}"
}

generate_internal_requests() {
  local count="$1"
  local run_id

  run_id="$(date +%s)"

  kubectl run "fake-web-${run_id}" \
    -n "${NAMESPACE}" \
    --image=curlimages/curl:8.7.1 \
    --restart=Never \
    --rm \
    --attach \
    --command -- \
    sh -c "i=1; while [ \$i -le ${count} ]; do curl -s http://${SERVICE_NAME} >/dev/null; echo request-\$i; i=\$((i+1)); sleep ${SLEEP_SECONDS}; done"
}

show_service_selector() {
  kubectl get svc "${SERVICE_NAME}" -n "${NAMESPACE}" -o jsonpath='{.spec.selector}'
  printf '\n'
}

require_kubectl

log "Routing external traffic to ${FROM_VERSION} only"
patch_service_version "${FROM_VERSION}"
log "Current selector: $(show_service_selector)"

log "Generating ${REQUEST_COUNT} fake web requests inside the cluster"
generate_internal_requests "${REQUEST_COUNT}"

FROM_COUNT="$(count_requests_for_version "${FROM_VERSION}")"
log "Observed ${FROM_COUNT} nginx access log entries on ${FROM_VERSION}"

if (( FROM_COUNT > THRESHOLD )); then
  log "Threshold ${THRESHOLD} exceeded, switching service selector to ${TO_VERSION}"
  patch_service_version "${TO_VERSION}"
else
  log "Threshold ${THRESHOLD} not exceeded, keeping selector on ${FROM_VERSION}"
fi

log "Current selector: $(show_service_selector)"

log "Generating ${VERIFY_COUNT} verification requests after the selector decision"
generate_internal_requests "${VERIFY_COUNT}"

TO_COUNT="$(count_requests_for_version "${TO_VERSION}")"
log "Observed ${TO_COUNT} nginx access log entries on ${TO_VERSION}"
log "Demo finished"
