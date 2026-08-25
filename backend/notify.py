"""
Module de notification.

Cette version est une préparation.
Pour la production, intégrer :
- Firebase Cloud Messaging pour Android ;
- Web Push pour PWA ;
- ou un fournisseur de notification transactionnelle.
"""

import json
import uuid
from datetime import datetime, timezone

import db


def queue_notification(
    target_request_id: str,
    title: str,
    body: str
):
    connection = db.get_connection()

    try:
        notification_id = str(uuid.uuid4())

        connection.execute(
            """
            INSERT INTO notifications (
                id,
                target_request_id,
                title,
                body,
                created_at,
                sent
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                target_request_id,
                title,
                body,
                datetime.now(timezone.utc).isoformat(),
                0
            )
        )

        connection.commit()

        return notification_id

    finally:
        connection.close()


def send_pending_notifications():
    """
    Cette fonction doit être remplacée par un appel réel à :
    - Firebase Cloud Messaging ;
    - Web Push ;
    - ou un service de notification.
    """

    connection = db.get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM notifications
            WHERE sent = 0
            """
        ).fetchall()

        for row in rows:
            print("Notification simulée :")
            print("Titre :", row["title"])
            print("Message :", row["body"])

            connection.execute(
                """
                UPDATE notifications
                SET sent = 1
                WHERE id = ?
                """,
                (row["id"],)
            )

        connection.commit()

        return len(rows)

    finally:
        connection.close()
