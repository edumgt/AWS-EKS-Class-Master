#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <cluster-name> [region]"
  exit 1
fi

CLUSTER_NAME="$1"
AWS_REGION="${2:-ap-northeast-2}"

kubectl create namespace amazon-cloudwatch --dry-run=client -o yaml | kubectl apply -f -

curl -s https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml \
  | sed "s/{{cluster_name}}/${CLUSTER_NAME}/;s/{{region_name}}/${AWS_REGION}/" \
  | kubectl apply -f -

echo "Installed Container Insights for cluster=${CLUSTER_NAME}, region=${AWS_REGION}"
