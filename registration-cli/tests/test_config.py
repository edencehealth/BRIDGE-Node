import json
from pathlib import Path

import registration_cli.config as config


def _patch_paths(tmp_path: Path, monkeypatch):
    cfg_dir = tmp_path / ".cfg"
    cfg_file = cfg_dir / "bridge-node-config.json"
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_file)
    return cfg_dir, cfg_file


def test_load_config_returns_defaults_when_no_file(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    cfg = config.load_config()
    assert cfg == config.DEFAULTS
    # must be a copy, not the shared DEFAULTS dict
    cfg["api_url"] = "mutated"
    assert config.DEFAULTS["api_url"] != "mutated"


def test_load_config_merges_file_over_defaults(tmp_path, monkeypatch):
    _, cfg_file = _patch_paths(tmp_path, monkeypatch)
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(json.dumps({"api_url": "https://override.example/api"}))

    cfg = config.load_config()
    assert cfg["api_url"] == "https://override.example/api"
    # keys not present in the file fall back to defaults
    assert cfg["oidc_token_url"] == config.DEFAULTS["oidc_token_url"]


def test_load_config_falls_back_on_corrupt_file(tmp_path, monkeypatch):
    _, cfg_file = _patch_paths(tmp_path, monkeypatch)
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("{ not valid json")

    assert config.load_config() == config.DEFAULTS


def test_save_config_value_round_trips_and_creates_dir(tmp_path, monkeypatch):
    cfg_dir, cfg_file = _patch_paths(tmp_path, monkeypatch)
    assert not cfg_dir.exists()

    config.save_config_value("api_url", "https://saved.example/api")

    assert cfg_file.exists()
    on_disk = json.loads(cfg_file.read_text())
    assert on_disk["api_url"] == "https://saved.example/api"
    # existing defaults are persisted alongside the new value
    assert on_disk["oidc_token_url"] == config.DEFAULTS["oidc_token_url"]


def test_default_api_url_has_no_double_slash():
    # Guards against the malformed default registration URL.
    assert "//api" not in config.DEFAULTS["api_url"].replace("https://", "")


def test_default_dcr_url_present_and_well_formed():
    url = config.DEFAULTS["dcr_url"]
    assert url.endswith("/clients-registrations/openid-connect")
    # no accidental double slash in the path (same class of bug as api_url)
    assert "//clients" not in url.replace("https://", "")
