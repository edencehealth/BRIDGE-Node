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

    _SECRET_FIELDS = ("client_secret", "registration_access_token")

    def __repr_args__(self):
        # Mask secret fields in repr/str/pretty output (e.g. pytest --showlocals)
        # without affecting attribute access or model_dump serialization.
        for key, value in super().__repr_args__():
            yield key, "***" if key in self._SECRET_FIELDS else value


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
