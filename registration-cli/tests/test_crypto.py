import stat
import sys

import pytest

from registration_cli import crypto


def test_generates_keypair_when_missing(tmp_path):
    key_path = tmp_path / "id_rsa"
    pub = crypto.generate_ssh_key_if_missing(key_path)

    assert key_path.exists()
    assert key_path.with_suffix(".pub").exists()
    assert pub.startswith("ssh-rsa ")
    assert pub.endswith(f"bridge-{__import__('socket').gethostname()}")
    # the returned string matches the persisted public key
    assert pub == key_path.with_suffix(".pub").read_text().strip()


def test_returns_existing_key_without_regenerating(tmp_path):
    key_path = tmp_path / "id_rsa"
    first = crypto.generate_ssh_key_if_missing(key_path)
    private_before = key_path.read_bytes()

    second = crypto.generate_ssh_key_if_missing(key_path)

    assert first == second
    # private key untouched on the second call
    assert key_path.read_bytes() == private_before


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permissions")
def test_private_key_is_owner_only(tmp_path):
    key_path = tmp_path / "id_rsa"
    crypto.generate_ssh_key_if_missing(key_path)
    mode = stat.S_IMODE(key_path.stat().st_mode)
    assert mode == 0o600


def test_creates_parent_directory(tmp_path):
    key_path = tmp_path / "nested" / ".ssh" / "id_rsa"
    crypto.generate_ssh_key_if_missing(key_path)
    assert key_path.exists()


def test_existing_private_key_not_overwritten_when_public_missing(tmp_path):
    key_path = tmp_path / "id_rsa"
    first_pub = crypto.generate_ssh_key_if_missing(key_path)
    private_before = key_path.read_bytes()

    # Simulate a lost/removed public key file
    key_path.with_suffix(".pub").unlink()

    second_pub = crypto.generate_ssh_key_if_missing(key_path)

    # Private key must NOT be regenerated/overwritten
    assert key_path.read_bytes() == private_before
    # Public key restored, derived from the existing private key
    assert key_path.with_suffix(".pub").exists()
    assert second_pub == first_pub
