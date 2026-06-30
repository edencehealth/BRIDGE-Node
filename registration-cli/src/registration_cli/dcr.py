import logging

import requests

from .credentials import IssuedClientCredentials

logger = logging.getLogger(__name__)


class DcrError(Exception):
    """Raised when Keycloak Dynamic Client Registration fails."""
    pass


def register_oidc_client(
    dcr_url: str,
    initial_access_token: str,
    client_name: str,
    timeout: int = 10,
) -> IssuedClientCredentials:
    """
    Register a confidential OIDC client at Keycloak via Dynamic Client
    Registration, authenticated with a one-time Initial Access Token.

    Never logs the Initial Access Token or the issued client_secret.
    """
    response = requests.post(
        dcr_url,
        json={
            "client_name": client_name,
            "grant_types": ["client_credentials"],
            "token_endpoint_auth_method": "client_secret_basic",
        },
        headers={
            "Authorization": f"Bearer {initial_access_token}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )

    if response.status_code == 401:
        logger.error("DCR rejected the Initial Access Token (401)")
        raise DcrError(
            "Initial Access Token invalid or expired — "
            "request a new one from your administrator."
        )

    if response.status_code != 201:
        logger.error("DCR error: status=%s body=%s", response.status_code, response.text)
        raise DcrError(f"Error {response.status_code}: {response.text}")

    try:
        data = response.json()
    except ValueError as exc:
        logger.error("DCR returned a non-JSON 201 response")
        raise DcrError(f"DCR returned a non-JSON response: {exc}") from exc
    logger.info("DCR succeeded; issued client_id=%s", data.get("client_id"))
    try:
        return IssuedClientCredentials(
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            registration_access_token=data["registration_access_token"],
            registration_client_uri=data["registration_client_uri"],
        )
    except KeyError as exc:
        raise DcrError(f"DCR response missing expected field: {exc}") from exc
