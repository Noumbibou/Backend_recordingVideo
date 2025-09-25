# Backend Recording Video - README

## Aperçu

Backend Django/DRF qui gère:
- Authentification (login JWT, register), profils (`UserProfile`), rôles.
- Gestion des campagnes vidéo (`VideoCampaign`) et questions.
- Invitations candidats (création de sessions d'entretien `InterviewSession`).
- Réponses vidéo, évaluations, analytics, uploads S3 présignés.

Code principal dans `interviews/`:
- `models.py`: modèles (HiringManager, Candidate, VideoCampaign, InterviewSession, VideoResponse, Evaluation, ...)
- `serializers.py`: sérialiseurs DRF.
- `views.py`: endpoints (ViewSets et APIViews).
- `urls.py`: routes API sous `/api/` (monté par `backend/urls.py`).


## Prérequis

- Python 3.10+
- Pipenv ou venv + pip
- PostgreSQL (recommandé) ou SQLite pour dev
- Variables d'environnement (voir `.env`)


## Installation

```bash
# Créer et activer un venv
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1

# Installer les dépendances
pip install -r requirements.txt

# Migrer la base
python manage.py migrate

# Créer un superuser (optionnel)
python manage.py createsuperuser
```


## Configuration (.env)

Fichier: `Backend_recordingVideo/.env`

Clés typiques:
```
DEBUG=true
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Base de données (ex. PostgreSQL)
DB_NAME=recording
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5432

# Email (Gmail SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=app-password
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=your@gmail.com

# AWS S3 (uploads vidéo optionnels)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_REGION=eu-west-1
```

Vérifiez `backend/settings.py` pour les noms exacts pris en charge et la logique CORS/DB/Email.


## Lancer le serveur

```bash
python manage.py runserver 0.0.0.0:8000
```

API accessible via: `http://localhost:8000/api/`


## Authentification

- JWT via `rest_framework_simplejwt`
- Endpoints:
  - `POST /api/auth/login/`  body: `{ email|username, password }`
  - `POST /api/auth/register/`  body: dépend du rôle, voir ci-dessous
  - `POST /api/auth/refresh/`
  - `POST /api/auth/verify/`
  - `GET  /api/auth/me/` (profil normalisé)

### Rôles et inscription

- Recruteur (`hiring_manager`)
  - Peut s'inscrire librement
  - Body minimal:
    ```json
    {
      "role": "hiring_manager",
      "username": "rh_paris",
      "email": "rh@entreprise.com",
      "password": "***",
      "first_name": "Alice",
      "last_name": "Martin",
      "company": "Entreprise SA",
      "department": "RH",
      "phone": "+33 6 12 34 56 78"
    }
    ```

- Candidat (`candidate`)
  - Deux chemins possibles:
    1) Invité préalablement: un utilisateur placeholder (username=email, mot de passe inutilisable) est créé lors de l'invitation. L'inscription « active » ce compte en posant le mot de passe.
    2) Non invité: auto-inscription autorisée avec les champs requis.
  - Body minimal:
    ```json
    {
      "role": "candidate",
      "email": "candidat@mail.com",
      "password": "***",
      "first_name": "Jean",
      "last_name": "Dupont",
      "phone": "+33 6 00 00 00 00",
      "linkedin_url": "https://www.linkedin.com/in/jean-dupont"
    }
    ```


## Endpoints clés

- Campagnes
  - `GET/POST /api/campaigns/`
  - `GET/PUT/PATCH/DELETE /api/campaigns/{id}/`
  - `POST /api/campaigns/{id}/invite-candidate/`  body: `{ email, first_name, last_name, phone, linkedin_url }`
  - `GET  /api/campaigns/{id}/sessions/`  (sessions liées à la campagne du recruteur)

- Sessions d'entretien
  - `GET/POST /api/sessions/` (recruteur: filtrées par ses campagnes)
  - `POST /api/sessions/{id}/start/`
  - `POST /api/sessions/{id}/submit-response/`

- Candidats
  - `GET /api/candidates/`  (recruteur: liste uniquement des candidats liés à ses campagnes via des sessions)

- Candidat (self-service)
  - `GET /api/candidate/interviews/`  (liste des sessions du candidat connecté)
  - `GET /api/candidate/interviews/{session_id}/`  (détails complet)

- Auth profil
  - `GET /api/auth/me/`  (profil et rôle normalisés)

- Upload vidéo (S3 presign)
  - `POST /api/presign-upload/` body: `{ campaign_id, session_id, filename, max_mb }`


## Flux métier principaux

- Création de campagne:
  1. Le recruteur crée la campagne et ses questions.
  2. Validation serveur: `start_date >= now` et `end_date > start_date`.

- Invitation candidat:
  1. `POST /api/campaigns/{id}/invite-candidate/`
  2. Si le candidat n'existe pas, création d'un `User` placeholder (username=email, mot de passe inutilisable), `UserProfile`(candidate) et `Candidate`.
  3. Création d'une `InterviewSession` liée à la campagne et au candidat.
  4. Envoi d'email d'invitation (si EMAIL_* configurés).

- Inscription candidat:
  - Invité sans mot de passe: l'inscription définit son mot de passe et complète/actualise la fiche `Candidate`.
  - Non invité: un `User` + `UserProfile(candidate)` + `Candidate` sont créés directement.


## Administration

- Django admin: `/admin/`
- Modèles enregistrés (extraits): `HiringManager`, `Candidate`, `VideoCampaign`, `InterviewSession`, `VideoResponse`, `Evaluation`, `DashboardMetrics`, ...


## Tests rapides

- Créer superuser et accéder à `/admin/`.
- Créer une campagne via `/api/campaigns/` (ou UI front), vérifier les dates.
- Inviter un candidat et vérifier `/api/campaigns/{id}/sessions/`.
- Inscrire le candidat via `/api/auth/register/`.


## Dépannage

- 400 à l'inscription candidat "compte déjà actif": l'email possède déjà un mot de passe utilisable → utiliser `/api/auth/login/`.
- 403 à l'inscription candidat "réservée aux invités": utilisez l'auto-inscription (sans placeholder) ou invitez d'abord.
- CORS: ajuster `CORS_ALLOWED_ORIGINS` dans `.env`/`settings.py`.
- Upload S3: vérifier `AWS_*` et la politique du bucket.
