from unittest.mock import MagicMock, patch

import pytest

from registration_cli import dcr
from registration_cli.credentials import IssuedClientCredentials

DCR_URL = "https://kc.example/realms/BRIDGE/clients-registrations/openid-connect"

DCR_RESPONSE = {
    "client_id": "generated-id",
    "client_secret": "generated-secret",
    "registration_access_token": "rat-xyz",
    "registration_client_uri": "https://kc.example/clients/generated-id",
}


@patch("registration_cli.dcr.requests.post")
def test_register_oidc_client_success(mock_post):
    mock_post.return_value = MagicMock(status_code=201, json=lambda: DCR_RESPONSE)

    creds = dcr.register_oidc_client(DCR_URL, "iat-123", "bridge-node-Test")

    assert isinstance(creds, IssuedClientCredentials)
    assert creds.client_id == "generated-id"
    assert creds.registration_access_token == "rat-xyz"

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer iat-123"
    assert kwargs["json"]["client_name"] == "bridge-node-Test"
    assert kwargs["json"]["grant_types"] == ["client_credentials"]
    assert kwargs["json"]["token_endpoint_auth_method"] == "client_secret_basic"


@patch("registration_cli.dcr.requests.post")
def test_register_oidc_client_expired_iat_raises_clear_error(mock_post):
    mock_post.return_value = MagicMock(status_code=401, text="invalid_token")

    with pytest.raises(dcr.DcrError) as exc:
        dcr.register_oidc_client(DCR_URL, "bad", "bridge-node-Test")
    assert "Initial Access Token" in str(exc.value)


@patch("registration_cli.dcr.requests.post")
def test_register_oidc_client_other_error_includes_status(mock_post):
    mock_post.return_value = MagicMock(status_code=400, text="bad request")

    with pytest.raises(dcr.DcrError) as exc:
        dcr.register_oidc_client(DCR_URL, "iat", "bridge-node-Test")
    assert "400" in str(exc.value)
