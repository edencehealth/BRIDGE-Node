#!/bin/bash
set -e

# Install curl if not found
if ! command -v curl &> /dev/null; then
    echo "Installing curl..."
    sudo apt-get update && sudo apt-get install -y curl
fi

# Install uv if not found
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env
    # source $HOME/.cargo/env
else
   echo "[INFO] uv already installed"
fi

# Check if Python3 is installed
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

# Install venv if needed
if ! command -v venv >/dev/null 2>&1; then
    echo "[INFO] Installing venv..."
    sudo apt-get install python3.12-venv
else
    echo "[INFO] venv already installed"
fi

#  Create a virtual environment
echo "[INFO] Starting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install python dependencies
pip3 install --upgrade pip
pip3 install -r requirements.txt

# 'uv run' will automatically:
# Run the registration code
echo "[INFO] Launching BRIDGE Node Registration App..."
uv run --project registration-cli python -m registration_cli.main register

# Install docker and related packages
echo "[INFO] Installing and setting up docker and related packages..."
# Add Docker's official GPG key:
sudo apt-get update && sudo apt upgrade -y
sudo apt-get install ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \ 
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo groupadd docker
sudo usermod -aG docker $USER

# Install ssh
echo "[INFO] Installing necessary packages..."
sudo apt install openssh-server
service ssh restart
service ssh status

echo "[INFO] Done."