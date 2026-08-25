import os
import time
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

SESSIONS = {}


def verify_admin(username: str, password: str):
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if not admin_username or not admin_password_hash:
        return None

    if username != admin_username:
        return None

    try:
        ph.verify(admin_password_hash, password)
    except VerifyMismatchError:
        return None
    except Exception:
        return None

    if ph.check_needs_rehash(admin_password_hash):
        # Dans une version avec base de données, mettre à jour le hash ici.
        pass

    token = secrets.token_urlsafe(32)
    ttl = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))

    SESSIONS[token] = {
        "username": username,
        "exp": time.time() + ttl
    }

    return token


def validate_token(token: str):
    if not token or token not in SESSIONS:
        return None

    session = SESSIONS[token]

    if time.time() > session["exp"]:
        SESSIONS.pop(token, None)
        return None

    return {
        "username": session["username"]
    }
