"""Generate a production-compatible AES-256-GCM key.

Usage:
    python scripts/generate_token_encryption_key.py

To write/replace TOKEN_ENCRYPTION_KEY in the local .env file:
    python scripts/generate_token_encryption_key.py --write-env

Never commit .env or expose a production key in source control.
"""

from __future__ import annotations

import argparse
import base64
import secrets
from pathlib import Path


def generate_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def write_env(key: str, path: Path) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("TOKEN_ENCRYPTION_KEY="):
            lines[index] = f"TOKEN_ENCRYPTION_KEY={key}"
            break
    else:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"TOKEN_ENCRYPTION_KEY={key}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write the generated key to the local .env file.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Environment file to update when --write-env is used.",
    )
    args = parser.parse_args()

    key = generate_key()
    if args.write_env:
        write_env(key, Path(args.env_file))
        print(f"TOKEN_ENCRYPTION_KEY written to {args.env_file}")
    else:
        print(key)


if __name__ == "__main__":
    main()
