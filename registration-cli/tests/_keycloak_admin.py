"""Test-only helper for minting Keycloak Initial Access Tokens via the admin API."""
import requests


def _get_admin_token(admin_token_url: str, client_id: str, client_secret: str,
                     timeout: int = 10) -> str:
    resp = requests.post(
        admin_token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def mint_initial_access_token(
    keycloak_base_url: str,
    realm: str,
    admin_token_url: str,
    admin_client_id: str,
    admin_client_secret: str,
    count: int = 1,
    expiration: int = 300,
    timeout: int = 10,
) -> str:
    """Create a single-use Keycloak Initial Access Token and return its value."""
    admin_token = _get_admin_token(
        admin_token_url, admin_client_id, admin_client_secret, timeout=timeout
    )
    url = f"{keycloak_base_url.rstrip('/')}/admin/realms/{realm}/clients-initial-access"
    resp = requests.post(
        url,
        json={"count": count, "expiration": expiration},
        headers={
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["token"]
