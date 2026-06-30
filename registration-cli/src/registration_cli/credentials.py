import json
from typing import Optional

from pydantic import BaseModel

from . import config

CREDENTIALS_FILE = config.CONFIG_DIR / "node-credentials.json"


class IssuedClientCredentials(BaseModel):
    """OIDC client credentials issued to this node by Keycloak DCR."""
    client_id: str
    client_secret: str
    registration_access_token: str
    registration_client_uri: str


def load() -> Optional[IssuedClientCredentials]:
    """Return the persisted node credentials, or None if not registered yet."""
    if not CREDENTIALS_FILE.exists():
        return None
    return IssuedClientCredentials(**json.loads(CREDENTIALS_FILE.read_text()))


def save(creds: IssuedClientCredentials) -> None:
    """Persist node credentials with owner-only (0600) permissions."""
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(creds.model_dump_json(indent=2))
    CREDENTIALS_FILE.chmod(0o600)
