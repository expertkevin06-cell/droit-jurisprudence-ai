import os

import db
from argon2 import PasswordHasher


def main():
    username = os.getenv("ADMIN_USERNAME")
    plain = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")

    if not username or not plain:
        print("Bootstrap admin ignoré.")
        return

    ph = PasswordHasher()
    password_hash = ph.hash(plain)

    db.init_db()

    connection = db.get_connection()

    try:
        connection.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, 'admin')
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash
            """,
            (username, password_hash)
        )
        connection.commit()
        print("ADMIN_BOOTSTRAP_OK")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
