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
else
   echo "[INFO] uv already installed"
fi

# Run the Node registration CLI
# 'uv run' will automatically:
#  - Download the correct Python version (if missing)
#  - Create a virtual environment
#  - Install dependencies
#  - Run the registration code
echo "[INFO] Launching BRIDGE Node Registration App..."
uv run --project registration-cli python -m registration_cli.main register

# Install docker and related packages if not found
if ! command -v docker &>/ /dev/null; then
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
else
    echo "[INFO] Docker and related packages already installed"
fi

sudo groupadd docker
sudo usermod -aG docker $USER
sudo systemctl enable docker

# Install ssh
if ! command -v openssh-server &>/ /dev/null; then
    echo "[INFO] Installing necessary packages..."
    sudo apt install openssh-server
    service ssh restart
else
    echo "[INFO] openssh-server already installed"
fi

sudo service ssh status --no-pager
echo "[INFO] Done."