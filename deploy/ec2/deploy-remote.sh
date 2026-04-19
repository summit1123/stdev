#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SHARED_DIR="${KWAIL_SHARED_DIR:-/opt/kwail/shared}"
PROJECT_DIR="${KWAIL_PROJECT_ROOT:-/opt/kwail/app}"
DEPLOY_ENV_FILE="${SHARED_DIR}/deploy.env"
DEFAULT_ELEVENLABS_VOICE_ID="hpp4J3VqNfWAUOO0d1Us"
DEFAULT_ELEVENLABS_VOICE_LABEL="Bella"

if [[ -f "${DEPLOY_ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${DEPLOY_ENV_FILE}"
  set +a
fi

upsert_runtime_env() {
  local key="$1"
  local value="$2"
  local target="${SHARED_DIR}/runtime.env"

  mkdir -p "${SHARED_DIR}"
  touch "${target}"

  if grep -q "^${key}=" "${target}"; then
    sed -i.bak "s#^${key}=.*#${key}=${value}#" "${target}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${target}"
  fi

  rm -f "${target}.bak"
}

if [[ -n "${API_DOMAIN:-}" ]]; then
  upsert_runtime_env "PUBLIC_API_BASE_URL" "https://${API_DOMAIN}"
fi

upsert_runtime_env "TTS_PROVIDER" "elevenlabs"
upsert_runtime_env "ELEVENLABS_VOICE_ID" "${ELEVENLABS_VOICE_ID:-${DEFAULT_ELEVENLABS_VOICE_ID}}"
upsert_runtime_env "ELEVENLABS_VOICE_LABEL" "${ELEVENLABS_VOICE_LABEL:-${DEFAULT_ELEVENLABS_VOICE_LABEL}}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

write_secret_env() {
  : "${SSM_PARAMETER_PREFIX:?SSM_PARAMETER_PREFIX is required}"

  local target="${SHARED_DIR}/secrets.env"
  : > "${target}"

  for key in OPENAI_API_KEY ELEVENLABS_API_KEY; do
    value="$(aws ssm get-parameter \
      --name "${SSM_PARAMETER_PREFIX}/${key}" \
      --with-decryption \
      --query 'Parameter.Value' \
      --output text)"
    printf '%s=%s\n' "${key}" "${value}" >> "${target}"
  done
}

require_cmd git
require_cmd pnpm
require_cmd docker
require_cmd aws

cd "${PROJECT_DIR}"
git fetch origin "${REPO_BRANCH:-main}"
git checkout "${REPO_BRANCH:-main}"
git reset --hard "origin/${REPO_BRANCH:-main}"

corepack enable
pnpm install --frozen-lockfile

if [[ -n "${API_DOMAIN:-}" ]]; then
  export VITE_API_BASE_URL="https://${API_DOMAIN}"
fi

pnpm --dir apps/web build
write_secret_env

export KWAIL_SHARED_DIR="${SHARED_DIR}"
docker compose -f deploy/ec2/compose.yml up -d --build --remove-orphans
docker image prune -f >/dev/null 2>&1 || true
