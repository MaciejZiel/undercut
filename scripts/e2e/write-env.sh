#!/usr/bin/env bash
# Writes the .env used by docker compose in the e2e job and exports the shared token to the
# next steps. Secrets are random per run and masked in the log.
set -euo pipefail

revalidate_secret="$(openssl rand -hex 24)"
internal_token="$(openssl rand -hex 24)"
echo "::add-mask::${revalidate_secret}"
echo "::add-mask::${internal_token}"

cat > .env <<ENV
REVALIDATE_SECRET=${revalidate_secret}
INTERNAL_API_TOKEN=${internal_token}
DJANGO_DEBUG=true
HTTP_PORT=8080
ENV

if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "E2E_INTERNAL_TOKEN=${internal_token}" >> "${GITHUB_ENV}"
fi
