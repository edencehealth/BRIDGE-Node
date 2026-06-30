from unittest.mock import MagicMock

from tests import _keycloak_admin


def _ok(json_body):
    resp = MagicMock(status_code=200, json=lambda: json_body)
    resp.raise_for_status = lambda: None
    return resp


def test_mint_initial_access_token_returns_token(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) == 1:
            return _ok({"access_token": "admin-tok"})
        return _ok({"token": "iat-xyz", "id": "abc", "count": 1})

    monkeypatch.setattr(_keycloak_admin.requests, "post", fake_post)

    token = _keycloak_admin.mint_initial_access_token(
        keycloak_base_url="https://kc.example/",
        realm="BRIDGE",
        admin_token_url="https://kc.example/realms/master/protocol/openid-connect/token",
        admin_client_id="admin-cli",
        admin_client_secret="secret",
    )

    assert token == "iat-xyz"
    assert len(calls) == 2

    # Call 1: admin client_credentials token grant
    admin_url, admin_kwargs = calls[0]
    assert admin_url == "https://kc.example/realms/master/protocol/openid-connect/token"
    assert admin_kwargs["data"]["grant_type"] == "client_credentials"
    assert admin_kwargs["data"]["client_id"] == "admin-cli"
    assert admin_kwargs["data"]["client_secret"] == "secret"

    # Call 2: create initial access token (note single rstrip of base URL)
    iat_url, iat_kwargs = calls[1]
    assert iat_url == "https://kc.example/admin/realms/BRIDGE/clients-initial-access"
    assert iat_kwargs["json"] == {"count": 1, "expiration": 300}
    assert iat_kwargs["headers"]["Authorization"] == "Bearer admin-tok"
