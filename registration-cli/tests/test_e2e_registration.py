"""Gated end-to-end registration test against live Keycloak + staging BRIDGE API.

Runs only when BRIDGE_E2E=1 and the admin env vars are set; otherwise skips.
See docs/superpowers/specs/2026-06-30-e2e-registration-test-design.md.
"""
import os
import uuid
import warnings
from dataclasses import dataclass

import pytest
import requests

from registration_cli import config, crypto, dcr
from registration_cli.registration_client import RegistrationClient
from tests import _keycloak_admin


@dataclass
class _E2EConfig:
    keycloak_base_url: str
    realm: str
    admin_token_url: str
    admin_client_id: str
    admin_client_secret: str
    api_url: str
    token_url: str
    dcr_url: str


def _e2e_env() -> _E2EConfig:
    """Read E2E env; skip the test if the gate or any required value is missing."""
    if os.environ.get("BRIDGE_E2E") != "1":
        pytest.skip("BRIDGE_E2E not set; skipping live end-to-end test")

    required = {
        "keycloak_base_url": "BRIDGE_E2E_KEYCLOAK_BASE_URL",
        "admin_token_url": "BRIDGE_E2E_ADMIN_TOKEN_URL",
        "admin_client_id": "BRIDGE_E2E_ADMIN_CLIENT_ID",
        "admin_client_secret": "BRIDGE_E2E_ADMIN_CLIENT_SECRET",
    }
    values = {}
    missing = []
    for field, env_name in required.items():
        v = os.environ.get(env_name)
        if not v:
            missing.append(env_name)
        values[field] = v
    if missing:
        pytest.skip(f"Missing required E2E env vars: {', '.join(missing)}")

    return _E2EConfig(
        keycloak_base_url=values["keycloak_base_url"],
        realm=os.environ.get("BRIDGE_E2E_REALM", "BRIDGE"),
        admin_token_url=values["admin_token_url"],
        admin_client_id=values["admin_client_id"],
        admin_client_secret=values["admin_client_secret"],
        api_url=os.environ.get("BRIDGE_E2E_API_URL", config.DEFAULTS["api_url"]),
        token_url=os.environ.get("BRIDGE_E2E_TOKEN_URL", config.DEFAULTS["oidc_token_url"]),
        dcr_url=os.environ.get("BRIDGE_E2E_DCR_URL", config.DEFAULTS["dcr_url"]),
    )


def _delete_oidc_client(registration_client_uri: str, registration_access_token: str,
                        timeout: int = 10) -> None:
    """Best-effort RFC 7592 delete of the OIDC client created via DCR."""
    try:
        resp = requests.delete(
            registration_client_uri,
            headers={"Authorization": f"Bearer {registration_access_token}"},
            timeout=timeout,
        )
        if resp.status_code not in (200, 204):
            warnings.warn(
                f"E2E cleanup: failed to delete OIDC client "
                f"({resp.status_code}): {resp.text}"
            )
    except Exception as exc:  # cleanup must never mask the test result
        warnings.warn(f"E2E cleanup: error deleting OIDC client: {exc}")


@pytest.mark.e2e
def test_register_flow_end_to_end_with_single_use_iat(tmp_path):
    env = _e2e_env()
    suffix = uuid.uuid4().hex[:8]

    # 1. Mint a single-use Initial Access Token via the Keycloak admin API
    iat = _keycloak_admin.mint_initial_access_token(
        keycloak_base_url=env.keycloak_base_url,
        realm=env.realm,
        admin_token_url=env.admin_token_url,
        admin_client_id=env.admin_client_id,
        admin_client_secret=env.admin_client_secret,
        count=1,
        expiration=300,
    )

    # 2. Throwaway SSH key (never touches ~/.ssh)
    public_key = crypto.generate_ssh_key_if_missing(tmp_path / "id_rsa")
    assert public_key.startswith("ssh-rsa ")

    # 3. DCR: register a confidential OIDC client at live Keycloak
    creds = dcr.register_oidc_client(env.dcr_url, iat, f"bridge-node-e2e-{suffix}")
    assert creds.client_id
    assert creds.client_secret

    try:
        # 4. Register the site at the BRIDGE API (assertion boundary)
        client = RegistrationClient(
            api_url=env.api_url,
            oidc_token_url=env.token_url,
            oidc_client_id=creds.client_id,
            oidc_client_secret=creds.client_secret,
        )
        resp = client.register_site(site_name=f"e2e-{suffix}", public_key=public_key)

        assert resp.id
        assert resp.site_name == f"e2e-{suffix}"
        assert resp.github_repo_name
        assert resp.github_org_name

        # 5. Single-use proof: reusing the spent IAT must be rejected
        with pytest.raises(dcr.DcrError):
            dcr.register_oidc_client(env.dcr_url, iat, f"bridge-node-e2e-{suffix}-2")
    finally:
        # 6. Cleanup: delete the OIDC client this test created
        _delete_oidc_client(creds.registration_client_uri, creds.registration_access_token)
