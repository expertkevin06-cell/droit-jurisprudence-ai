import json
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

import db

load_dotenv()


def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def insert_sources(connection):
    sources = load_json_file("sources.json")["sources"]

    for source in sources:
        connection.execute(
            """
            INSERT INTO legal_sources (
                id,
                name,
                url,
                type,
                trust_level,
                primary_source,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                url = excluded.url,
                type = excluded.type,
                trust_level = excluded.trust_level,
                primary_source = excluded.primary_source,
                description = excluded.description
            """,
            (
                source["id"],
                source["name"],
                source["url"],
                source["type"],
                source["trust_level"],
                1 if source.get("primary") else 0,
                source.get("description", "")
            )
        )


def insert_case_law_placeholders(connection):
    case_law = [
        {
            "id": "placeholder_vices_caches",
            "court": "À compléter depuis source officielle",
            "decision_date": None,
            "reference": "À compléter",
            "themes": ["vices_caches"],
            "actors": [
                "vendeur_professionnel",
                "vendeur_particulier",
                "acheteur"
            ],
            "summary": "Décision relative aux vices cachés à importer depuis une source officielle.",
            "url": "https://www.courdecassation.fr/",
            "source_id": "cour_cassation",
            "verified": False
        },
        {
            "id": "placeholder_conformite",
            "court": "À compléter depuis source officielle",
            "decision_date": None,
            "reference": "À compléter",
            "themes": ["garantie_legale_conformite"],
            "actors": [
                "vendeur_professionnel",
                "acheteur"
            ],
            "summary": "Décision relative à la garantie légale de conformité à importer depuis une source officielle.",
            "url": "https://www.legifrance.gouv.fr/",
            "source_id": "legifrance",
            "verified": False
        },
        {
            "id": "placeholder_reparateur",
            "court": "À compléter depuis source officielle",
            "decision_date": None,
            "reference": "À compléter",
            "themes": ["reparateur_responsabilite"],
            "actors": [
                "reparateur_professionnel",
                "proprietaire_vehicule"
            ],
            "summary": "Décision relative à la responsabilité du réparateur automobile à importer depuis une source officielle.",
            "url": "https://www.courdecassation.fr/",
            "source_id": "cour_cassation",
            "verified": False
        }
    ]

    for decision in case_law:
        connection.execute(
            """
            INSERT INTO case_law (
                id,
                court,
                decision_date,
                reference,
                themes,
                actors,
                summary,
                url,
                source_id,
                verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                court = excluded.court,
                decision_date = excluded.decision_date,
                reference = excluded.reference,
                themes = excluded.themes,
                actors = excluded.actors,
                summary = excluded.summary,
                url = excluded.url,
                source_id = excluded.source_id,
                verified = excluded.verified
            """,
            (
                decision["id"],
                decision["court"],
                decision["decision_date"],
                decision["reference"],
                json.dumps(decision["themes"], ensure_ascii=False),
                json.dumps(decision["actors"], ensure_ascii=False),
                decision["summary"],
                decision["url"],
                decision["source_id"],
                1 if decision["verified"] else 0
            )
        )


def insert_admin_user(connection):
    username = os.getenv("ADMIN_USERNAME")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if not username or not password_hash:
        print("ADMIN_USERNAME ou ADMIN_PASSWORD_HASH manquant dans .env.")
        return

    connection.execute(
        """
        INSERT INTO users (
            username,
            password_hash,
            role
        )
        VALUES (?, ?, 'admin')
        ON CONFLICT(username) DO UPDATE SET
            password_hash = excluded.password_hash
        """,
        (
            username,
            password_hash
        )
    )


def main():
    db.init_db()

    connection = db.get_connection()

    try:
        insert_sources(connection)
        insert_case_law_placeholders(connection)
        insert_admin_user(connection)

        connection.commit()

        print("Base SQLite initialisée.")
        print(f"Chemin : {db.DB_PATH}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
