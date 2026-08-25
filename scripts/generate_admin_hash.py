#!/usr/bin/env python3
"""
Génère un hash Argon2 pour le mot de passe admin.

Usage :
    python scripts/generate_admin_hash.py

Ne collez jamais votre mot de passe en clair dans un fichier.
"""

import getpass

from argon2 import PasswordHasher


def main():
    ph = PasswordHasher()

    password = getpass.getpass("Mot de passe admin : ")
    confirm = getpass.getpass("Confirmation : ")

    if password != confirm:
        print("Erreur : les mots de passe ne correspondent pas.")
        return

    password_hash = ph.hash(password)

    print("\nCopiez cette valeur dans backend/.env :")
    print(f"ADMIN_PASSWORD_HASH={password_hash}")


if __name__ == "__main__":
    main()
