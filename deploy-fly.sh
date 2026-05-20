#!/usr/bin/env bash
set -euo pipefail
APP_NAME="${FLY_APP_NAME:-app-damp-sun-5680}"
TOKEN="${FLY_API_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "Set FLY_API_TOKEN in the environment or export it before running."
  echo "Example: export FLY_API_TOKEN=\"your_token\""
  exit 1
fi

if ! command -v flyctl >/dev/null 2>&1; then
  echo "flyctl is not installed. Install from https://fly.io/docs/hands-on/install-flyctl/"
  exit 1
fi

echo "Authenticating with Fly..."
flyctl auth login --access-token "$TOKEN"

echo "Deploying $APP_NAME..."
flyctl deploy -a "$APP_NAME" --config ./fly.toml
