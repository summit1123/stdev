#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/infra/inventory"

mkdir -p "${OUT_DIR}"

run_json() {
  local name="$1"
  shift

  echo ">> ${name}"
  if "$@" > "${OUT_DIR}/${name}.json"; then
    echo "   wrote infra/inventory/${name}.json"
  else
    echo "   failed: ${name}" >&2
    rm -f "${OUT_DIR}/${name}.json"
    return 1
  fi
}

run_text() {
  local name="$1"
  shift

  echo ">> ${name}"
  if "$@" > "${OUT_DIR}/${name}.txt"; then
    echo "   wrote infra/inventory/${name}.txt"
  else
    echo "   failed: ${name}" >&2
    rm -f "${OUT_DIR}/${name}.txt"
    return 1
  fi
}

echo "AWS inventory output directory: ${OUT_DIR}"
echo

run_json identity aws sts get-caller-identity
run_text configure aws configure list
run_json s3-buckets aws s3api list-buckets
run_json route53-zones aws route53 list-hosted-zones
run_json cloudfront-distributions aws cloudfront list-distributions
run_json acm-certificates aws acm list-certificates --region us-east-1
run_json ecr-repositories aws ecr describe-repositories
run_json apprunner-services aws apprunner list-services
run_json ecs-clusters aws ecs list-clusters
run_json lambda-functions aws lambda list-functions
run_json rds-instances aws rds describe-db-instances

echo
echo "Inventory complete."
