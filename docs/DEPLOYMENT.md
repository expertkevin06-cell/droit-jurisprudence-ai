# Déploiement Justice Auto Robuste

## 1. Prérequis

- Python 3.12 ;
- Docker ;
- un serveur HTTPS ;
- un nom de domaine ;
- Node.js ou PWABuilder pour générer l’APK.

## 2. Installation locale

Cloner le projet :

```bash
git clone <votre-repo>
cd justice-auto-robuste
```

Créer l’environnement backend :

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 3. Générer le hash admin

Depuis la racine :

```bash
python scripts/generate_admin_hash.py
```

Copier le hash dans :

```text
backend/.env
```

Exemple :

```env
ADMIN_USERNAME=ExpertKF
ADMIN_PASSWORD_HASH=$argon2id$...
```

## 4. Valider la base juridique

Depuis `backend` :

```bash
python validator.py
```

## 5. Lancer le backend

```bash
uvicorn main:app --reload
```

API :

```text
http://127.0.0.1:8000
```

## 6. Lancer le frontend

Depuis `frontend` :

```bash
python -m http.server 3000
```

Frontend :

```text
http://127.0.0.1:3000
```

## 7. Docker

Depuis la racine :

```bash
docker compose up --build
```

## 8. Production

En production :

- le backend doit être accessible en HTTPS ;
- le frontend doit être accessible en HTTPS ;
- le fichier `frontend/index.html` doit contenir l’URL réelle de l’API :

```javascript
const CONFIG = {
    apiUrl: "https://api.votre-domaine.com"
};
```

## 9. Génération APK

1. Héberger le frontend en HTTPS.
2. Vérifier que la PWA est valide.
3. Aller sur PWABuilder :

```text
https://www.pwabuilder.com/
```

4. Entrer l’URL du frontend.
5. Générer le package Android.
6. Télécharger l’APK ou le projet Android Studio.
7. Signer l’APK si nécessaire.
