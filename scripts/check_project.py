#!/usr/bin/env python3
"""
Vérifie que les fichiers principaux du projet Justice Auto Robuste existent.
"""

import os
import sys

REQUIRED_FILES = [
    "README.md",
    "docker-compose.yml",
    ".gitignore",

    "backend/main.py",
    "backend/auth.py",
    "backend/validator.py",
    "backend/rag.py",
    "backend/sources.json",
    "backend/legal_kb.json",
    "backend/requirements.txt",
    "backend/.env.example",
    "backend/Dockerfile",

    "frontend/index.html",
    "frontend/manifest.json",
    "frontend/sw.js",
]


def main():
    missing = []

    for file_path in REQUIRED_FILES:
        if not os.path.exists(file_path):
            missing.append(file_path)

    if missing:
        print("Fichiers manquants :")
        for item in missing:
            print("-", item)
        sys.exit(1)

    print("Structure du projet OK.")


if __name__ == "__main__":
    main()
