import os
import time
import secrets
import sqlite3

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

import db

ph = PasswordHasher()

MEMORY_SESSIONS = {}


def _get_user_from_db(username: str):
    connection = None

    try:
        connection = db.get_connection()

        row = connection.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if row:
            return dict(row)

        return None

    except sqlite3.Error:
        return None

    finally:
        if connection:
            connection.close()


def _get_env_admin_hash(username: str):
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if not admin_username or not admin_password_hash:
        return None

    if username != admin_username:
        return None

    return admin_password_hash


def _store_session_in_db(token: str, username: str, expires_at: float):
    connection = None

    try:
        connection = db.get_connection()

        connection.execute(
            """
            INSERT OR REPLACE INTO sessions (
                token,
                username,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (
                token,
                username,
                expires_at
            )
        )

        connection.commit()

    except sqlite3.Error:
        MEMORY_SESSIONS[token] = {
            "username": username,
            "exp": expires_at
        }

    finally:
        if connection:
            connection.close()


def _get_session_from_db(token: str):
    connection = None

    try:
        connection = db.get_connection()

        row = connection.execute(
            """
            SELECT *
            FROM sessions
            WHERE token = ?
            """,
            (token,)
        ).fetchone()

        if row:
            return dict(row)

        return None

    except sqlite3.Error:
        return None

    finally:
        if connection:
            connection.close()


def _delete_session_from_db(token: str):
    connection = None

    try:
        connection = db.get_connection()

        connection.execute(
            """
            DELETE FROM sessions
            WHERE token = ?
            """,
            (token,)
        )

        connection.commit()

    except sqlite3.Error:
        pass

    finally:
        if connection:
            connection.close()


def verify_admin(username: str, password: str):
    password_hash = None

    user = _get_user_from_db(username)

    if user:
        password_hash = user.get("password_hash")
    else:
        password_hash = _get_env_admin_hash(username)

    if not password_hash:
        return None

    try:
        ph.verify(password_hash, password)
    except VerifyMismatchError:
        return None
    except Exception:
        return None

    if ph.check_needs_rehash(password_hash):
        # Dans une version avancée, mettre à jour le hash dans la base.
        pass

    token = secrets.token_urlsafe(32)
    ttl = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))
    expires_at = time.time() + ttl

    _store_session_in_db(token, username, expires_at)

    return token


def validate_token(token: str):
    if not token:
        return None

    session = _get_session_from_db(token)

    if session:
        if time.time() > session.get("expires_at", 0):
            _delete_session_from_db(token)
            return None

        return {
            "username": session.get("username")
        }

    memory_session = MEMORY_SESSIONS.get(token)

    if not memory_session:
        return None

    if time.time() > memory_session.get("exp", 0):
        MEMORY_SESSIONS.pop(token, None)
        return None

    return {
        "username": memory_session.get("username")
    }
