#!/usr/bin/env bash
#
# Run the end-to-end BRIDGE Node registration test against live Keycloak +
# the BRIDGE registration API.
#
# Required values are prompted interactively when not already set in the
# environment. The admin client secret is read without echoing. Everything
# runs in this script's own process, so the entered secret never leaks into
# your interactive shell.
#
# Optional endpoint overrides (export before running to target a
# non-production environment; otherwise the test uses production defaults and
# warns):
#   BRIDGE_E2E_REALM      (default: BRIDGE)
#   BRIDGE_E2E_API_URL
#   BRIDGE_E2E_TOKEN_URL
#   BRIDGE_E2E_DCR_URL
#
# Any extra arguments are forwarded to pytest, e.g.:
#   ./run-e2e-test.sh -x -s
#
set -euo pipefail

prompt_required() {
    # Usage: prompt_required VAR_NAME "Prompt text" [default] [secret]
    local var_name="$1" prompt_text="$2" default="${3:-}" secret="${4:-}"

    if [ -n "${!var_name:-}" ]; then
        return 0  # already provided via the environment
    fi

    local display_prompt="$prompt_text"
    if [ -n "$default" ]; then
        display_prompt="$prompt_text [$default]"
    fi

    local value
    if [ "$secret" = "secret" ]; then
        read -r -s -p "$display_prompt: " value
        echo  # newline after the hidden input
    else
        read -r -p "$display_prompt: " value
    fi

    if [ -z "$value" ]; then
        value="$default"  # empty input falls back to the default (if any)
    fi
    if [ -z "$value" ]; then
        echo "Error: $var_name is required." >&2
        exit 1
    fi
    export "$var_name=$value"
}

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 'uv' is not installed or not on PATH." >&2
    exit 1
fi

echo "[INFO] BRIDGE Node end-to-end registration test"
echo "[INFO] Enter the Keycloak admin credentials used to mint a single-use Initial Access Token."

prompt_required BRIDGE_E2E_KEYCLOAK_BASE_URL "Keycloak base URL" "https://keycloak.bridge.cloud.edence.health"

# Default the admin token URL to the BRIDGE-realm token endpoint on that server
# (where the admin service-account client used to mint the IAT lives).
default_admin_token_url="${BRIDGE_E2E_KEYCLOAK_BASE_URL%/}/realms/BRIDGE/protocol/openid-connect/token"

prompt_required BRIDGE_E2E_ADMIN_TOKEN_URL   "Keycloak admin token URL" "$default_admin_token_url"
prompt_required BRIDGE_E2E_ADMIN_CLIENT_ID   "Keycloak admin client ID"
prompt_required BRIDGE_E2E_ADMIN_CLIENT_SECRET "Keycloak admin client secret" "" secret

echo "[INFO] Optional overrides (export before running to target non-production):"
echo "       BRIDGE_E2E_REALM (default: BRIDGE), BRIDGE_E2E_API_URL, BRIDGE_E2E_TOKEN_URL, BRIDGE_E2E_DCR_URL"

# Run from this script's directory (the registration-cli project root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export BRIDGE_E2E=1
echo "[INFO] Running end-to-end registration test..."
exec uv run pytest -m e2e -v "$@"
