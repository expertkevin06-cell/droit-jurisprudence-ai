#!/usr/bin/env bash

set -e

echo "Vérification de la structure du projet..."
python scripts/check_project.py

echo "Validation de la base juridique..."
cd backend
python validator.py

echo "Lancement du backend..."
uvicorn main:app --reload --port 8000 &

cd ../frontend

echo "Lancement du frontend..."
python -m http.server 3000
