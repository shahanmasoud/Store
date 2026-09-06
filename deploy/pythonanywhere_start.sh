#!/usr/bin/env bash
set -euo pipefail

: "${DOMAIN_SOCKET:?PythonAnywhere did not provide DOMAIN_SOCKET}"

ENV_FILE="${HOME}/.store.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# PythonAnywhere Bash consoles provide these automatically, while the ASGI
# launcher may not. urllib needs them to reach the allowlisted outbound proxy.
export http_proxy="${http_proxy:-http://proxy.server:3128}"
export https_proxy="${https_proxy:-http://proxy.server:3128}"

exec "${HOME}/.virtualenvs/store/bin/uvicorn" \
  --app-dir "${HOME}/Store/backend" \
  --uds "${DOMAIN_SOCKET}" \
  app.main:app
