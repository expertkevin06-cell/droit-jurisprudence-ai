# Justice Auto Robuste

Application PWA/APK d'information juridique automobile basée sur des sources officielles gratuites.

## Avertissement

Cette application fournit une information juridique à titre indicatif.
Elle ne constitue pas une consultation juridique et ne remplace pas un avocat.

## Sources principales

- Legifrance
- Service-public.fr
- Cour de cassation
- Conseil d'État
- EUR-Lex
- Data.gouv.fr
- Ministère de la Justice
- Ministère de l'Intérieur
- Sécurité routière
- DGCCRF
- CNIL
- Défenseur des droits

## Sources doctrinales secondaires

- Dalloz, uniquement contenus légalement accessibles
- HAL Science
- OpenEdition
- Cairn gratuit
- Persée

## Installation backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Générer le mot de passe admin hashé

```bash
python - <<'PY'
from argon2 import PasswordHasher
ph = PasswordHasher()
print(ph.hash("Kevin.83600"))
PY
```

Copier le hash dans `.env` :

```env
ADMIN_USERNAME=ExpertKF
ADMIN_PASSWORD_HASH=$argon2id$...
```

## Valider la base juridique

```bash
python validator.py
```

## Lancer le backend

```bash
uvicorn main:app --reload
```

## Lancer le frontend

Ouvrir `frontend/index.html` avec un serveur statique.

Exemple :

```bash
cd frontend
python -m http.server 3000
```

## Docker

```bash
docker compose up --build
```

Backend :

```text
http://127.0.0.1:8000
```

Frontend :

```text
http://127.0.0.1:3000
```

## IA locale gratuite

Installer Ollama puis :

```bash
ollama pull mistral
```

Dans `.env` :

```env
LLM_PROVIDER=ollama
OLLAMA_API_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=mistral
```

## Génération APK

1. Héberger le frontend en HTTPS.
2. Héberger le backend en HTTPS.
3. Modifier `CONFIG.apiUrl` dans `frontend/index.html`.
4. Aller sur PWABuilder.
5. Générer le package Android.

## Sécurité

Ne jamais laisser le mot de passe en clair dans le frontend.
Le mot de passe doit être hashé côté serveur.
