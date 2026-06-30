from unittest.mock import MagicMock, patch
import logging

import pytest

from registration_cli.registration_client import (
    RegistrationApiError,
    RegistrationClient,
    SiteRegistrationResponse,
)

API_URL = "https://portal.example/api/v1/register"
TOKEN_URL = "https://kc.example/token"

VALID_RESPONSE = {
    "id": 42,
    "site_name": "Test Site",
    "created_at": "2026-01-01T12:00:00+00:00",
    "created_by": "tester",
    "github_repo_name": "node-test-site",
    "github_org_name": "edencehealth",
}


def _client():
    return RegistrationClient(
        api_url=API_URL,
        oidc_token_url=TOKEN_URL,
        oidc_client_id="cid",
        oidc_client_secret="secret",
    )


def test_api_url_trailing_slash_is_stripped():
    client = RegistrationClient(
        api_url=API_URL + "///",
        oidc_token_url=TOKEN_URL,
        oidc_client_id="cid",
        oidc_client_secret="secret",
    )
    assert client.api_url == API_URL


@patch("registration_cli.registration_client.requests.post")
def test_get_jwt_access_token_uses_client_credentials(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200, json=lambda: {"access_token": "tok-123"}
    )
    token = _client()._get_jwt_access_token()

    assert token == "tok-123"
    _, kwargs = mock_post.call_args
    assert kwargs["data"]["grant_type"] == "client_credentials"
    assert kwargs["data"]["client_id"] == "cid"
    assert kwargs["data"]["client_secret"] == "secret"


@patch.object(RegistrationClient, "_get_jwt_access_token", return_value="tok-123")
@patch("registration_cli.registration_client.requests.post")
def test_register_site_success(mock_post, _mock_token):
    response = MagicMock(status_code=201, json=lambda: VALID_RESPONSE)
    mock_post.return_value = response

    result = _client().register_site(site_name="Test Site", public_key="ssh-rsa AAAA")

    assert isinstance(result, SiteRegistrationResponse)
    assert result.id == 42
    assert result.github_org_name == "edencehealth"

    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {"site_name": "Test Site", "public_key": "ssh-rsa AAAA"}
    assert kwargs["headers"]["Authorization"] == "Bearer tok-123"


@patch.object(RegistrationClient, "_get_jwt_access_token", return_value="tok-123")
@patch("registration_cli.registration_client.requests.post")
def test_register_site_non_201_raises(mock_post, _mock_token):
    mock_post.return_value = MagicMock(
        status_code=400, text="bad request", json=lambda: {"detail": "bad"}
    )

    with pytest.raises(RegistrationApiError) as exc:
        _client().register_site(site_name="Test Site", public_key="ssh-rsa AAAA")
    assert "400" in str(exc.value)


@patch.object(RegistrationClient, "_get_jwt_access_token", return_value="tok-123")
@patch("registration_cli.registration_client.requests.post")
def test_register_site_propagates_network_error(mock_post, _mock_token):
    mock_post.side_effect = ConnectionError("boom")

    with pytest.raises(ConnectionError):
        _client().register_site(site_name="Test Site", public_key="ssh-rsa AAAA")


def test_safe_json_swallows_errors():
    bad = MagicMock()
    bad.json.side_effect = ValueError("no json")
    assert RegistrationClient._safe_json(bad) is None


def test_legacy_argv_main_is_removed():
    import registration_cli.registration_client as rc
    assert not hasattr(rc, "main")


@patch.object(RegistrationClient, "_get_jwt_access_token", return_value="supersecret-token")
def test_get_headers_does_not_log_access_token(_mock_token, caplog):
    with caplog.at_level(logging.DEBUG):
        headers = _client()._get_headers()
    assert headers["Authorization"] == "Bearer supersecret-token"
    assert "supersecret-token" not in caplog.text
