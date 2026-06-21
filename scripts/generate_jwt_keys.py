"""Generate RSA-2048 key pair for JWT signing (RS256).

Outputs:
  instance/keys/jwt-private.pem  — RSA private key (keep secret!)
  instance/keys/jwt-public.pem   — RSA public key (safe to distribute)

Usage:
  python scripts/generate_jwt_keys.py
  python scripts/generate_jwt_keys.py --force       # overwrite existing keys
  python scripts/generate_jwt_keys.py --bits 4096   # use 4096-bit key
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEY_DIR = REPO_ROOT / "instance" / "keys"


def generate_keypair(key_dir: Path, bits: int = 2048, force: bool = False) -> None:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    private_path = key_dir / "jwt-private.pem"
    public_path = key_dir / "jwt-public.pem"

    if private_path.exists() and not force:
        print(f"Private key already exists at {private_path}. Use --force to overwrite.")
        sys.exit(1)

    key_dir.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=bits,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_path.write_bytes(private_pem)
    private_path.chmod(0o600)
    print(f"Private key written to {private_path}")

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_path.write_bytes(public_pem)
    print(f"Public key written to {public_path}")

    _print_env_hints(private_path, public_path)


def _print_env_hints(private_path: Path, public_path: Path) -> None:
    import base64

    priv_b64 = base64.b64encode(private_path.read_bytes()).decode()
    pub_b64 = base64.b64encode(public_path.read_bytes()).decode()
    print("\n# Add to config/secret.cfg or environment:")
    print(f"API_JWT_RSA_PRIVATE_KEY={priv_b64}")
    print(f"API_JWT_RSA_PUBLIC_KEYS={pub_b64}")
    print(f"# Or use file paths in config:")
    print(f"JWT_PRIVATE_KEY_PATH={private_path}")
    print(f"JWT_PUBLIC_KEY_PATH={public_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RSA key pair for JWT RS256 signing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing keys")
    parser.add_argument("--bits", type=int, default=2048, choices=[2048, 4096], help="Key size in bits")
    parser.add_argument("--key-dir", type=str, default=str(DEFAULT_KEY_DIR), help="Output directory")
    args = parser.parse_args()
    generate_keypair(Path(args.key_dir), bits=args.bits, force=args.force)


if __name__ == "__main__":
    main()