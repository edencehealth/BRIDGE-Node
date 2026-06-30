import stat
import sys

import pytest

import registration_cli.config as config
from registration_cli import credentials
from registration_cli.credentials import IssuedClientCredentials

CREDS = IssuedClientCredentials(
    client_id="cid",
    client_secret="sec",
    registration_access_token="rat",
    registration_client_uri="https://kc.example/clients/cid",
)


def _patch_paths(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".cfg"
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(credentials, "CREDENTIALS_FILE", cfg_dir / "node-credentials.json")
    return cfg_dir


def test_load_returns_none_when_absent(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    assert credentials.load() is None


def test_save_then_load_round_trips(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    credentials.save(CREDS)
    assert credentials.load() == CREDS


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permissions")
def test_saved_file_is_owner_only(tmp_path, monkeypatch):
    cfg_dir = _patch_paths(tmp_path, monkeypatch)
    credentials.save(CREDS)
    mode = stat.S_IMODE((cfg_dir / "node-credentials.json").stat().st_mode)
    assert mode == 0o600


def test_repr_and_str_mask_secrets_but_dump_does_not():
    creds = IssuedClientCredentials(
        client_id="cid",
        client_secret="SECRETVALUE",
        registration_access_token="TOKENVALUE",
        registration_client_uri="https://kc.example/clients/cid",
    )
    for rendered in (repr(creds), str(creds)):
        assert "SECRETVALUE" not in rendered
        assert "TOKENVALUE" not in rendered
        assert "cid" in rendered  # non-secret fields still visible
        assert "***" in rendered
    # Persistence must still serialize the real secret values.
    dumped = creds.model_dump_json()
    assert "SECRETVALUE" in dumped
    assert "TOKENVALUE" in dumped
