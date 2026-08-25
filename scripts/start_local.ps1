Write-Host "Vérification de la structure du projet..."
python scripts/check_project.py

Write-Host "Validation de la base juridique..."
Set-Location backend
python validator.py

Write-Host "Lancement du backend..."
Start-Process -NoNewWindow uvicorn -ArgumentList "main:app", "--reload", "--port", "8000"

Set-Location ../frontend

Write-Host "Lancement du frontend..."
python -m http.server 3000
