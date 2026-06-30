import os
import socket
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def _public_key_str(private_key) -> str:
    """Render an OpenSSH public-key line (with a bridge host comment) for a key."""
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )
    comment = f"bridge-{socket.gethostname()}"
    return f"{public_bytes.decode('utf-8')} {comment}"


def _write_public_key(public_key_path: Path, public_key_str: str) -> None:
    with open(public_key_path, "w", encoding="utf-8") as f:
        f.write(public_key_str)


def generate_ssh_key_if_missing(key_path: Path) -> str:
    """Return the SSH public key, generating a keypair only if no private key exists.

    If a private key is already present, it is never overwritten: the public key
    is derived from it (and written back if the .pub file is missing).
    """
    private_key_path = key_path
    public_key_path = key_path.with_suffix(".pub")

    # Never clobber an existing private key — derive the public key from it.
    if private_key_path.exists():
        private_key = serialization.load_pem_private_key(
            private_key_path.read_bytes(), password=None, backend=default_backend()
        )
        public_key_str = _public_key_str(private_key)
        if not public_key_path.exists():
            _write_public_key(public_key_path, public_key_str)
        return public_key_str

    # No private key yet: generate a fresh pair.
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )

    # Create the private key file with 0600 from the start (no umask race window).
    key_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(private_key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with open(fd, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    public_key_str = _public_key_str(key)
    _write_public_key(public_key_path, public_key_str)
    return public_key_str
