from __future__ import annotations

from argon2 import PasswordHasher

_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password_hash, password)
