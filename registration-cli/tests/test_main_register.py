from datetime import datetime, timezone
from types import SimpleNamespace

from typer.testing import CliRunner

from registration_cli import main as cli_main
from registration_cli.credentials import IssuedClientCredentials

runner = CliRunner()

ISSUED = IssuedClientCredentials(
    client_id="node-cid",
    client_secret="node-secret",
    registration_access_token="rat",
    registration_client_uri="https://kc.example/clients/node-cid",
)


def _fake_response():
    return SimpleNamespace(
        id=7,
        site_name="Test Site",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        created_by="tester",
        github_repo_name="node-test-site",
        github_org_name="edencehealth",
    )


class _FakeClient:
    def __init__(self, **kwargs):
        _FakeClient.kwargs = kwargs

    def register_site(self, site_name, public_key):
        _FakeClient.called_with = {"site_name": site_name, "public_key": public_key}
        return _fake_response()


def _patch_common(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_main.crypto, "generate_ssh_key_if_missing", lambda p: "ssh-rsa AAAA test")
    monkeypatch.setattr(cli_main, "RegistrationClient", _FakeClient)
    monkeypatch.setattr(cli_main.Repo, "clone_from", lambda url, dest: None)
    monkeypatch.setattr(cli_main, "DESTINATION_DIR", tmp_path / "ohdsi")
    monkeypatch.setattr(cli_main, "VOCAB_DIR", tmp_path / "ohdsi" / "vocab")
    monkeypatch.setattr(cli_main, "OUTPUT_DIR", tmp_path / "ohdsi" / "output")


def test_first_run_registers_client_and_persists(monkeypatch, tmp_path):
    _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(cli_main.credentials, "load", lambda: None)
    saved = []
    monkeypatch.setattr(cli_main.credentials, "save", lambda c: saved.append(c))
    dcr_calls = []

    def fake_dcr(dcr_url, iat, client_name):
        dcr_calls.append((dcr_url, iat, client_name))
        return ISSUED

    monkeypatch.setattr(cli_main.dcr, "register_oidc_client", fake_dcr)

    result = runner.invoke(
        cli_main.app,
        ["register", "--site-name", "Test Site"],
        input="my-iat-token\n",
    )

    assert result.exit_code == 0, result.output
    assert dcr_calls == [(cli_main.APP_CONFIG.get("dcr_url"), "my-iat-token", "bridge-node-Test Site")]
    assert saved == [ISSUED]
    assert _FakeClient.kwargs["oidc_client_id"] == "node-cid"
    assert _FakeClient.kwargs["oidc_client_secret"] == "node-secret"
    assert (tmp_path / "ohdsi" / "vocab").exists()
    assert (tmp_path / "ohdsi" / "output").exists()


def test_reuse_persisted_credentials_skips_dcr(monkeypatch, tmp_path):
    _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(cli_main.credentials, "load", lambda: ISSUED)

    def fail_dcr(*args, **kwargs):
        raise AssertionError("DCR must not run when credentials are already persisted")

    monkeypatch.setattr(cli_main.dcr, "register_oidc_client", fail_dcr)

    result = runner.invoke(cli_main.app, ["register", "--site-name", "Test Site"])

    assert result.exit_code == 0, result.output
    assert _FakeClient.kwargs["oidc_client_id"] == "node-cid"
    assert _FakeClient.called_with["public_key"] == "ssh-rsa AAAA test"


def test_corrupt_credentials_exits_cleanly(monkeypatch, tmp_path):
    """A corrupt credentials file must produce a clean exit code 1, not a traceback."""
    _patch_common(monkeypatch, tmp_path)

    def raise_value_error():
        raise ValueError("corrupt")

    monkeypatch.setattr(cli_main.credentials, "load", raise_value_error)

    result = runner.invoke(cli_main.app, ["register", "--site-name", "Test Site"])

    assert result.exit_code != 0
