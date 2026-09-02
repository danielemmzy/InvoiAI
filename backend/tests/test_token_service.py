from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest

from app2.services.token_service import TokenService


class FakeRepository:
    pass


def service(monkeypatch):
    key = base64.urlsafe_b64encode(b"x" * 32).decode().rstrip("=")
    monkeypatch.setattr(
        "app.services.token_service.settings.token_encryption_key",
        key,
    )
    return TokenService(repository=FakeRepository())


def test_token_round_trip(monkeypatch):
    tokens = service(monkeypatch)

    encrypted = tokens.encrypt("refresh-secret")

    assert encrypted.startswith("v1.")
    assert encrypted != "refresh-secret"
    assert tokens.decrypt(encrypted) == "refresh-secret"


def test_encryption_is_randomized(monkeypatch):
    tokens = service(monkeypatch)

    first = tokens.encrypt("same-secret")
    second = tokens.encrypt("same-secret")

    assert first != second
    assert tokens.decrypt(first) == tokens.decrypt(second) == "same-secret"


def test_tampered_token_is_rejected(monkeypatch):
    tokens = service(monkeypatch)

    encrypted = tokens.encrypt("secret")
    parts = encrypted.split(".")

    # Decode the actual ciphertext+authentication tag.
    ciphertext = bytearray(tokens._b64decode(parts[2]))

    # Flip a real ciphertext bit.
    ciphertext[0] ^= 0x01

    # Re-encode the modified bytes.
    parts[2] = tokens._b64(bytes(ciphertext))

    with pytest.raises(ValueError, match="decryption failed"):
        tokens.decrypt(".".join(parts))
