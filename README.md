# Artonomy

Artonomy is a Django web platform for artists. Artists get a public profile and portfolio, publish art posts, sell products and offer services, and can be discovered through a category-based explore section. A "spotlight" system with stars, referrals, and boosts helps promote profiles, and the site includes homepage ads, support tickets, and visit tracking for admins.

## Features

- Accounts: signup, login/logout, email verification (link and code), password reset
- Artist profiles at `/accounts/u/<username>/` with skills, testimonials, social links, client logos, and counters; profile dashboard
- Explore artists by category and subcategory (`/artists/explore/...`)
- Marketplace: art posts with images and likes, products, and services, each with per-user listings
- Spotlight: star transactions, referrals, and profile boosts
- Homepage advertisements and site-wide settings
- Support tickets
- Visit tracking middleware and an admin KPI page (`/kpi/`)
- Contact and About pages
- Management commands to import legacy users and roles

## Tech stack

- Python 3.12, Django 5.2
- PostgreSQL (psycopg2)
- Gunicorn, WhiteNoise
- Pillow, django-widget-tweaks, python-dotenv
- Docker / Docker Compose; GitHub Actions deploy over SSH

## Project structure

```
artonomy/       Project settings, root URLs, WSGI/ASGI
accounts/       Auth, email verification, profiles
artists/        Categories, subcategories, explore views
marketplace/    Art posts, products, services
spotlight/      Stars, referrals, boosts
core/           Site settings, visits, contact/about, KPI
advertisement/  Homepage ads
support/        Support tickets
templates/      Django templates
assets/         Source static files (collected into static/)
Dockerfile, docker-compose.dev.yml, entrypoint.sh
```

## Configuration

Create a `.env` file in the project root:

```
SECRET_KEY=change-me
DEBUG=False

DB_NAME=appdb
DB_USER=appuser
DB_PASSWORD=your-db-password
DB_HOST=db
DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=Artonomy <no-reply@example.com>
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email-user
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

`ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are set in `artonomy/settings.py`; add your own domain there.

## Running with Docker (development)

```bash
docker compose -f docker-compose.dev.yml up --build
```

This starts PostgreSQL and the web app. `entrypoint.sh` waits for the database, runs `collectstatic` and `migrate`, then starts `runserver` when `DJANGO_DEBUG=true` or Gunicorn otherwise. The app is served on http://127.0.0.1:5000/.

## Running locally without Docker

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

You need a running PostgreSQL instance matching the `DB_*` variables. Note: `requirements.txt` is saved as UTF-16; convert it to UTF-8 if pip cannot read it.

## Deployment

`.github/workflows/deploy.yml` deploys on push to `main`: it connects over SSH, pulls the code, rebuilds the `web` service with Docker Compose, runs migrations and `collectstatic`, and starts the `caddy` service. It requires the repository secrets `SSH_HOST`, `SSH_USER`, `SSH_KEY`, and `PROJECT_DIR`.
