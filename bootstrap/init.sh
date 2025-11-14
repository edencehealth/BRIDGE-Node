#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Configurable parameters
# -----------------------------
API_URL="http://portal.bridge.central/api/v1/register"
OIDC_TOKEN_URL="http://keycloak.bridge.central/realms/BRIDGE/protocol/openid-connect/token"
CLIENT_ID="bridge-node"
CLIENT_SECRET="*******"
SSH_KEY_PATH="$HOME/.ssh/bridge_github_key"
CLONE_DIR="/$HOME/bridge_ansible_playbook"
NODENAME="$HOSTNAME"

# -----------------------------
# Ensure dependencies
# -----------------------------

# Check if python3 is installed
echo "[INFO] Installing dependencies..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] Python3 is required but not installed."
  exit 1
fi

# Install pip if needed
if ! command -v pip3 >/dev/null 2>&1; then
  echo "[INFO] Installing pip..."
  sudo apt-get update && sudo apt-get install -y python3-pip
fi

# Install python dependencies
pip3 install --upgrade pip
if ! command -v ansible-playbook >/dev/null 2>&1; then
  echo "[INFO] Installing Ansible..."
  pip3 install --user --upgrade ansible requests pydantic
else
  pip3 install --user --upgrade requests pydantic
fi

# -----------------------------
# Generate SSH key pair
# -----------------------------
echo "[INFO] Generating SSH key..."
mkdir -p "$(dirname "$SSH_KEY_PATH")"
if [ ! -f "$SSH_KEY_PATH" ]; then
  ssh-keygen -t rsa -b 4096 -C "bridge-$NODENAME" -f "$SSH_KEY_PATH" -N ""
fi
PUBLIC_KEY=$(cat "${SSH_KEY_PATH}.pub")

SITE_NAME="TEST-$NODENAME"

# -----------------------------
# Register & fetch repo URL
# -----------------------------
echo "[INFO] Registering with BRIDGE registration API using OIDC client credentials..."
REGISTRATION_DETAILS=$(python3 register.py "$API_URL" "$SITE_NAME" "$PUBLIC_KEY" "$OIDC_TOKEN_URL" "$CLIENT_ID" "$CLIENT_SECRET")
echo "[INFO] Registration details: $REGISTRATION_DETAILS"

# -----------------------------
# Clone GitHub repo
# -----------------------------
#echo "[INFO] Cloning Ansible playbook..."
#eval "$(ssh-agent -s)"
#ssh-add "$SSH_KEY_PATH"
#
#rm -rf "$CLONE_DIR"
#git clone "$REPO_URL" "$CLONE_DIR"
#
## -----------------------------
## Run Ansible playbook
## -----------------------------
#echo "[INFO] Running Ansible playbook..."
#cd "$CLONE_DIR"
#
## Assumes repo has site.yml or main.yml as entrypoint
#if [ -f "site.yml" ]; then
#  ansible-playbook site.yml
#elif [ -f "main.yml" ]; then
#  ansible-playbook main.yml
#else
#  echo "[ERROR] Could not find site.yml or main.yml in playbook repo."
#  exit 1
#fi
#
#echo "[INFO] Done."