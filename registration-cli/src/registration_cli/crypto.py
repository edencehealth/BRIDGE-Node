import socket
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

def generate_ssh_key_if_missing(key_path: Path) -> str:
    """Generates an SSH key pair if one doesn't exist."""
    private_key_path = key_path
    public_key_path = key_path.with_suffix(".pub")

    if private_key_path.exists() and public_key_path.exists():
        return public_key_path.read_text().strip()

    # Generate Key
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )

    # Save Private Key
    key_path.parent.mkdir(parents=True, exist_ok=True)
    with open(private_key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    private_key_path.chmod(0o600)

    # Generate Public Key string
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )
    comment = f"bridge-{socket.gethostname()}"
    public_key_str = f"{public_bytes.decode('utf-8')} {comment}"

    with open(public_key_path, "w") as f:
        f.write(public_key_str)

    return public_key_str