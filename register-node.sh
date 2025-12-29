#!/bin/bash
set -e

# 1. Install uv if not found
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

2. Check if Python3 is installed
echo "[INFO] Installing dependencies..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] Python3 is required but not installed."
  exit 1
else
  echo "[INFO] Python3 already installed"
fi

# Install pip if needed
if ! command -v pip3 >/dev/null 2>&1; then
  echo "[INFO] Installing pip..."
  sudo apt-get update && sudo apt-get install -y python3-pip
else
  echo "[INFO] Pip already installed"
fi

#  Create a virtual environment
echo "Starting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install python dependencies
pip3 install --upgrade pip
pip3 install -r requirements.txt

# 'uv run' will automatically:
# 3. Run the registration code
echo "[INFO] Launching BRIDGE Node Registration App..."
uv run --project registration-cli python -m registration_cli.main register

# 4. Install docker and related packages
echo "[INFO] Installing and setting up docker and related packages..."
# Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo groupadd docker
sudo usermod -aG docker $USER

# Install ssh and git
echo "[INFO] Installing necessary packages..."
sudo apt install openssh-server
service ssh restart
service ssh status

echo "[INFO] Done."