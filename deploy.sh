#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ENV_FILE="${ROOT_DIR}/.env"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-${ROOT_DIR}/deploy.env}"

RUN_WEB=1
RUN_API=1
RUN_INFRA=1
RUN_HEALTHCHECK=1
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [options]

Options:
  --dry-run            Print commands without executing them.
  --skip-web           Skip the web deployment step.
  --skip-api           Skip the API deployment step.
  --skip-infra         Skip Terraform apply.
  --skip-healthcheck   Skip the final health check.
  --help               Show this message.

Environment variables:
  DEPLOY_TARGET                        Deploy mode. Use ec2-ssm for the EC2 runtime.
  DEPLOY_WEB_BUILD_CMD                Command to build the web app.
  DEPLOY_WEB_DIST_DIR                 Directory to sync to S3.
  DEPLOY_WEB_S3_BUCKET                Target S3 bucket for the web build.
  DEPLOY_WEB_S3_PREFIX                Optional key prefix inside the web bucket.
  DEPLOY_WEB_CLOUDFRONT_DISTRIBUTION_ID
                                      Optional CloudFront distribution to invalidate.
  DEPLOY_CLOUDFRONT_INVALIDATION_PATHS
                                      Space-separated invalidation paths. Default: /*
  DEPLOY_API_DEPLOY_CMD               Optional custom command that redeploys the API runtime.
  DEPLOY_API_ECR_REPOSITORY_URI       ECR repository URI for the API image.
  DEPLOY_API_APP_RUNNER_SERVICE_ARN   Optional App Runner service ARN to trigger after push.
  DEPLOY_API_IMAGE_TAG                Docker image tag. Default: current git short SHA or latest.
  DEPLOY_API_DOCKERFILE               Dockerfile path. Default: apps/api/Dockerfile
  DEPLOY_API_BUILD_CONTEXT            Docker build context. Default: apps/api
  DEPLOY_API_LOCAL_IMAGE_NAME         Local temporary image name. Default: kwail-api
  DEPLOY_API_START_DEPLOYMENT         Set to 1 to call aws apprunner start-deployment after push.
  DEPLOY_EC2_INSTANCE_ID              EC2 instance ID used by ec2-ssm mode.
  DEPLOY_EC2_PROJECT_ROOT             Project root on the instance. Default: /opt/kwail/app
  DEPLOY_EC2_DEPLOY_USER              OS user that runs the deploy script. Default: ubuntu
  DEPLOY_EC2_REMOTE_SCRIPT            Remote deploy script. Default: deploy/ec2/deploy-remote.sh
  DEPLOY_EC2_SSM_PARAMETER_PREFIX     SSM parameter prefix used for runtime secrets.
  DEPLOY_SECRET_ENV_KEYS              Space-separated env keys pushed to SSM. Default: OPENAI_API_KEY ELEVENLABS_API_KEY
  DEPLOY_RUN_TERRAFORM                Set to 1 to run Terraform apply.
  DEPLOY_TERRAFORM_DIR                Terraform root. Default: infra/service
  DEPLOY_TERRAFORM_INIT               Set to 1 to run terraform init before apply.
  DEPLOY_TERRAFORM_INIT_ARGS          Extra args for terraform init.
  DEPLOY_TERRAFORM_APPLY_ARGS         Extra args for terraform apply.
  DEPLOY_HEALTHCHECK_URL              Final URL to check with curl.
  DEPLOY_AWS_PROFILE                  Optional AWS profile override.
  DEPLOY_AWS_REGION                   Optional AWS region override.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    --skip-web)
      RUN_WEB=0
      ;;
    --skip-api)
      RUN_API=0
      ;;
    --skip-infra)
      RUN_INFRA=0
      ;;
    --skip-healthcheck)
      RUN_HEALTHCHECK=0
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

load_env_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${file}"
    set +a
  fi
}

load_env_file "${APP_ENV_FILE}"
load_env_file "${DEPLOY_ENV_FILE}"

if [[ -n "${DEPLOY_AWS_PROFILE:-}" ]]; then
  export AWS_PROFILE="${DEPLOY_AWS_PROFILE}"
fi

if [[ -n "${DEPLOY_AWS_REGION:-}" ]]; then
  export AWS_REGION="${DEPLOY_AWS_REGION}"
  export AWS_DEFAULT_REGION="${DEPLOY_AWS_REGION}"
fi

DEPLOY_WEB_BUILD_CMD="${DEPLOY_WEB_BUILD_CMD:-pnpm --dir apps/web build}"
DEPLOY_WEB_DIST_DIR="${DEPLOY_WEB_DIST_DIR:-apps/web/dist}"
DEPLOY_WEB_S3_PREFIX="${DEPLOY_WEB_S3_PREFIX:-}"
DEPLOY_CLOUDFRONT_INVALIDATION_PATHS="${DEPLOY_CLOUDFRONT_INVALIDATION_PATHS:-/*}"
DEPLOY_TERRAFORM_DIR="${DEPLOY_TERRAFORM_DIR:-infra/service}"
DEPLOY_TERRAFORM_INIT="${DEPLOY_TERRAFORM_INIT:-0}"
DEPLOY_TERRAFORM_INIT_ARGS="${DEPLOY_TERRAFORM_INIT_ARGS:-}"
DEPLOY_TERRAFORM_APPLY_ARGS="${DEPLOY_TERRAFORM_APPLY_ARGS:--auto-approve}"
DEPLOY_RUN_TERRAFORM="${DEPLOY_RUN_TERRAFORM:-0}"
DEPLOY_TARGET="${DEPLOY_TARGET:-legacy}"
DEPLOY_API_DOCKERFILE="${DEPLOY_API_DOCKERFILE:-apps/api/Dockerfile}"
DEPLOY_API_BUILD_CONTEXT="${DEPLOY_API_BUILD_CONTEXT:-apps/api}"
DEPLOY_API_LOCAL_IMAGE_NAME="${DEPLOY_API_LOCAL_IMAGE_NAME:-kwail-api}"
DEPLOY_API_START_DEPLOYMENT="${DEPLOY_API_START_DEPLOYMENT:-1}"
DEPLOY_EC2_PROJECT_ROOT="${DEPLOY_EC2_PROJECT_ROOT:-/opt/kwail/app}"
DEPLOY_EC2_DEPLOY_USER="${DEPLOY_EC2_DEPLOY_USER:-ubuntu}"
DEPLOY_EC2_REMOTE_SCRIPT="${DEPLOY_EC2_REMOTE_SCRIPT:-deploy/ec2/deploy-remote.sh}"
DEPLOY_SECRET_ENV_KEYS="${DEPLOY_SECRET_ENV_KEYS:-OPENAI_API_KEY ELEVENLABS_API_KEY}"

if git -C "${ROOT_DIR}" rev-parse --short HEAD >/dev/null 2>&1; then
  GIT_SHA="$(git -C "${ROOT_DIR}" rev-parse --short HEAD)"
else
  GIT_SHA="latest"
fi
DEPLOY_API_IMAGE_TAG="${DEPLOY_API_IMAGE_TAG:-${GIT_SHA}}"

log_step() {
  printf '\n==> %s\n' "$1"
}

run_cmd() {
  local cmd="$1"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '[dry-run] %s\n' "${cmd}"
    return 0
  fi
  bash -lc "cd \"${ROOT_DIR}\" && ${cmd}"
}

terraform_output_raw() {
  local output_name="$1"
  if [[ ! -d "${ROOT_DIR}/${DEPLOY_TERRAFORM_DIR}" ]]; then
    return 0
  fi
  terraform -chdir="${ROOT_DIR}/${DEPLOY_TERRAFORM_DIR}" output -raw "${output_name}" 2>/dev/null || true
}

hydrate_deploy_targets() {
  DEPLOY_WEB_S3_BUCKET="${DEPLOY_WEB_S3_BUCKET:-$(terraform_output_raw web_bucket_name)}"
  DEPLOY_WEB_CLOUDFRONT_DISTRIBUTION_ID="${DEPLOY_WEB_CLOUDFRONT_DISTRIBUTION_ID:-$(terraform_output_raw web_distribution_id)}"
  DEPLOY_API_ECR_REPOSITORY_URI="${DEPLOY_API_ECR_REPOSITORY_URI:-$(terraform_output_raw api_ecr_repository_url)}"
  DEPLOY_API_APP_RUNNER_SERVICE_ARN="${DEPLOY_API_APP_RUNNER_SERVICE_ARN:-$(terraform_output_raw api_service_arn)}"
  DEPLOY_EC2_INSTANCE_ID="${DEPLOY_EC2_INSTANCE_ID:-$(terraform_output_raw ec2_instance_id)}"
  DEPLOY_EC2_SSM_PARAMETER_PREFIX="${DEPLOY_EC2_SSM_PARAMETER_PREFIX:-$(terraform_output_raw ec2_ssm_parameter_prefix)}"
  DEPLOY_EC2_ORIGIN_URL="${DEPLOY_EC2_ORIGIN_URL:-$(terraform_output_raw ec2_origin_http_url)}"
  if [[ -z "${DEPLOY_HEALTHCHECK_URL:-}" ]]; then
    if [[ "${DEPLOY_TARGET}" == "ec2-ssm" && -n "${DEPLOY_EC2_ORIGIN_URL:-}" ]]; then
      DEPLOY_HEALTHCHECK_URL="${DEPLOY_EC2_ORIGIN_URL}/health"
    else
      DEPLOY_HEALTHCHECK_URL="$(terraform_output_raw api_url)"
    fi
  fi
}

trim_slashes() {
  local value="$1"
  value="${value#/}"
  value="${value%/}"
  printf '%s' "${value}"
}

join_s3_path() {
  local bucket="$1"
  local prefix
  prefix="$(trim_slashes "$2")"
  if [[ -n "${prefix}" ]]; then
    printf 's3://%s/%s' "${bucket}" "${prefix}"
  else
    printf 's3://%s' "${bucket}"
  fi
}

put_secure_parameter() {
  local name="$1"
  local value="$2"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '[dry-run] aws ssm put-parameter --name "%s" --type SecureString --overwrite --value "***"\n' "${name}"
    return 0
  fi
  aws ssm put-parameter --name "${name}" --type SecureString --overwrite --value "${value}" >/dev/null
}

sync_runtime_secrets() {
  if [[ -z "${DEPLOY_EC2_SSM_PARAMETER_PREFIX:-}" ]]; then
    echo "DEPLOY_EC2_SSM_PARAMETER_PREFIX is required for ec2-ssm mode." >&2
    exit 1
  fi

  log_step "Sync runtime secrets to SSM"
  local key value
  for key in ${DEPLOY_SECRET_ENV_KEYS}; do
    value="${!key:-}"
    if [[ -z "${value}" ]]; then
      echo "Missing required env value for ${key}." >&2
      exit 1
    fi
    put_secure_parameter "${DEPLOY_EC2_SSM_PARAMETER_PREFIX}/${key}" "${value}"
  done
}

run_remote_deploy_via_ssm() {
  if [[ -z "${DEPLOY_EC2_INSTANCE_ID:-}" ]]; then
    echo "DEPLOY_EC2_INSTANCE_ID is required for ec2-ssm mode." >&2
    exit 1
  fi

  log_step "Trigger remote deploy over SSM"

  local remote_cmd command_id parameters_json
  remote_cmd="sudo -u ${DEPLOY_EC2_DEPLOY_USER} -H bash -lc 'cd ${DEPLOY_EC2_PROJECT_ROOT} && ./${DEPLOY_EC2_REMOTE_SCRIPT}'"
  parameters_json="$(jq -cn --arg cmd "${remote_cmd}" '{commands: [$cmd]}')"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '[dry-run] aws ssm send-command --instance-ids "%s" --document-name AWS-RunShellScript --parameters %s\n' \
      "${DEPLOY_EC2_INSTANCE_ID}" "${parameters_json}"
    return 0
  fi

  command_id="$(
    aws ssm send-command \
      --instance-ids "${DEPLOY_EC2_INSTANCE_ID}" \
      --document-name "AWS-RunShellScript" \
      --comment "kwail deploy" \
      --parameters "${parameters_json}" \
      --query 'Command.CommandId' \
      --output text
  )"

  aws ssm wait command-executed \
    --command-id "${command_id}" \
    --instance-id "${DEPLOY_EC2_INSTANCE_ID}"

  aws ssm get-command-invocation \
    --command-id "${command_id}" \
    --instance-id "${DEPLOY_EC2_INSTANCE_ID}" \
    --output text \
    --query '[Status,StandardOutputContent,StandardErrorContent]'
}

if [[ "${RUN_INFRA}" -eq 1 && "${DEPLOY_RUN_TERRAFORM}" == "1" ]]; then
  if [[ "${DEPLOY_TERRAFORM_INIT}" == "1" ]]; then
    log_step "Terraform init"
    run_cmd "terraform -chdir=\"${DEPLOY_TERRAFORM_DIR}\" init ${DEPLOY_TERRAFORM_INIT_ARGS}"
  fi

  log_step "Terraform apply"
  run_cmd "terraform -chdir=\"${DEPLOY_TERRAFORM_DIR}\" apply ${DEPLOY_TERRAFORM_APPLY_ARGS}"
elif [[ "${RUN_INFRA}" -eq 1 ]]; then
  log_step "Terraform apply"
  echo "Skipping Terraform because DEPLOY_RUN_TERRAFORM is not set to 1."
fi

hydrate_deploy_targets

if [[ "${DEPLOY_TARGET}" == "ec2-ssm" ]]; then
  if [[ "${RUN_WEB}" -eq 1 || "${RUN_API}" -eq 1 ]]; then
    sync_runtime_secrets
    run_remote_deploy_via_ssm
  fi

  if [[ "${RUN_HEALTHCHECK}" -eq 1 ]]; then
    if [[ -n "${DEPLOY_HEALTHCHECK_URL:-}" ]]; then
      log_step "Health check"
      run_cmd "curl --fail --silent --show-error \"${DEPLOY_HEALTHCHECK_URL}\""
    else
      log_step "Health check"
      echo "Skipping health check because DEPLOY_HEALTHCHECK_URL is not set."
    fi
  fi

  printf '\nDeploy flow complete.\n'
  exit 0
fi

if [[ "${RUN_WEB}" -eq 1 ]]; then
  if [[ -z "${DEPLOY_WEB_S3_BUCKET:-}" ]]; then
    echo "DEPLOY_WEB_S3_BUCKET is required unless --skip-web is used." >&2
    exit 1
  fi

  log_step "Build web"
  run_cmd "${DEPLOY_WEB_BUILD_CMD}"

  log_step "Sync web assets to S3"
  WEB_S3_TARGET="$(join_s3_path "${DEPLOY_WEB_S3_BUCKET}" "${DEPLOY_WEB_S3_PREFIX}")"
  run_cmd "aws s3 sync \"${DEPLOY_WEB_DIST_DIR}\" \"${WEB_S3_TARGET}\" --delete"

  if [[ -n "${DEPLOY_WEB_CLOUDFRONT_DISTRIBUTION_ID:-}" ]]; then
    log_step "Invalidate CloudFront"
    run_cmd "aws cloudfront create-invalidation --distribution-id \"${DEPLOY_WEB_CLOUDFRONT_DISTRIBUTION_ID}\" --paths ${DEPLOY_CLOUDFRONT_INVALIDATION_PATHS}"
  fi
fi

if [[ "${RUN_API}" -eq 1 ]]; then
  log_step "Deploy API"
  if [[ -n "${DEPLOY_API_DEPLOY_CMD:-}" ]]; then
    run_cmd "${DEPLOY_API_DEPLOY_CMD}"
  elif [[ -n "${DEPLOY_API_ECR_REPOSITORY_URI:-}" ]]; then
    API_AWS_REGION="${DEPLOY_AWS_REGION:-${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-northeast-2}}}"
    API_ECR_REGISTRY="${DEPLOY_API_ECR_REPOSITORY_URI%%/*}"
    API_LOCAL_IMAGE_REF="${DEPLOY_API_LOCAL_IMAGE_NAME}:${DEPLOY_API_IMAGE_TAG}"
    API_REMOTE_IMAGE_REF="${DEPLOY_API_ECR_REPOSITORY_URI}:${DEPLOY_API_IMAGE_TAG}"

    run_cmd "aws ecr get-login-password --region \"${API_AWS_REGION}\" | docker login --username AWS --password-stdin \"${API_ECR_REGISTRY}\""
    run_cmd "docker build -f \"${DEPLOY_API_DOCKERFILE}\" -t \"${API_LOCAL_IMAGE_REF}\" \"${DEPLOY_API_BUILD_CONTEXT}\""
    run_cmd "docker tag \"${API_LOCAL_IMAGE_REF}\" \"${API_REMOTE_IMAGE_REF}\""
    run_cmd "docker push \"${API_REMOTE_IMAGE_REF}\""

    if [[ "${DEPLOY_API_START_DEPLOYMENT}" == "1" && -n "${DEPLOY_API_APP_RUNNER_SERVICE_ARN:-}" ]]; then
      run_cmd "aws apprunner start-deployment --service-arn \"${DEPLOY_API_APP_RUNNER_SERVICE_ARN}\""
    fi
  else
    echo "Skipping API deploy because neither DEPLOY_API_DEPLOY_CMD nor DEPLOY_API_ECR_REPOSITORY_URI is set."
  fi
fi

if [[ "${RUN_HEALTHCHECK}" -eq 1 ]]; then
  if [[ -n "${DEPLOY_HEALTHCHECK_URL:-}" ]]; then
    log_step "Health check"
    run_cmd "curl --fail --silent --show-error \"${DEPLOY_HEALTHCHECK_URL}\""
  else
    log_step "Health check"
    echo "Skipping health check because DEPLOY_HEALTHCHECK_URL is not set."
  fi
fi

printf '\nDeploy flow complete.\n'
