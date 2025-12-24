import json
from pathlib import Path
from typing import Dict

# Constants
APP_NAME = "BRIDGE-Node-Registration-CLI"
CONFIG_DIR = Path.home() / f".{APP_NAME}"
CONFIG_FILE = CONFIG_DIR / "bridge-node-config.json"
LOG_FILE = CONFIG_DIR / "bridge-node-registration.log"

# Default settings
DEFAULTS = {
    "api_url": "http://portal.bridge.central/api/v1/register",
    "oidc_token_url": "http://keycloak.bridge.central/realms/BRIDGE/protocol/openid-connect/token"
}

def load_config() -> Dict[str, str]:
    """Load config from disk or return defaults."""
    if not CONFIG_FILE.exists():
        return DEFAULTS.copy()
    try:
        with open(CONFIG_FILE, "r") as f:
            return {**DEFAULTS, **json.load(f)}
    except Exception:
        return DEFAULTS.copy()

def save_config_value(key: str, value: str):
    """Save a specific config value to disk."""
    current = load_config()
    current[key] = value
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(current, f, indent=4)