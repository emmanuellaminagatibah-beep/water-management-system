# Deployment Guide

This project is a Django application with PostgreSQL for hosted use and WhiteNoise for static assets. Hosting-provider settings belong in the provider's environment configuration; do not commit `.env` files or production secrets.

## Runtime

- Python 3.13
- PostgreSQL
- A TLS-terminating host or reverse proxy
- SMTP credentials if the application sends email

Install dependencies in the build environment:

```powershell
python -m pip install -r requirements.txt
```

## Required Environment

Set these values in the hosting provider's secret/environment panel:

```text
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<long randomly generated secret>
DJANGO_ALLOWED_HOSTS=app.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://app.example.com
WMS_DB_ENGINE=postgresql
EMAIL_HOST=<smtp host>
EMAIL_PORT=587
EMAIL_HOST_USER=<smtp user>
EMAIL_HOST_PASSWORD=<smtp password>
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=Agatibahsprings <noreply@example.com>
```

For Render, add the PostgreSQL database's **Internal Database URL** to the web
service as `DATABASE_URL`, and set `WMS_DB_ENGINE=postgresql`. The app accepts
that URL directly; the individual `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` variables are only
needed when `DATABASE_URL` is not set. Use the **External Database URL** for
connections from your local machine, not from the hosted web service.

Set `DJANGO_TRUST_X_FORWARDED_PROTO=true` only when the application is behind a trusted proxy that sets `X-Forwarded-Proto`. The default production configuration redirects to HTTPS and enables secure session/CSRF cookies. HSTS defaults to one year but does not automatically cover subdomains or opt into browser preload. Before enabling `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=true` or `DJANGO_SECURE_HSTS_PRELOAD=true`, verify every affected hostname serves HTTPS and that the domain owner intends the long-lived policy. Django may report HSTS deployment warnings until that domain-specific decision is made. `WMS_CONTACT_EMAIL`, `WMS_CONTACT_PHONE`, and `WMS_CONTACT_LOCATION` are optional public contact details.

Generate `DJANGO_SECRET_KEY` with a cryptographically secure generator, store it only in the provider's secret store, and use a different value for each environment. For example, run `python -c "import secrets; print(secrets.token_urlsafe(64))"` locally, then enter the result directly into the provider's secret manager. Never commit the value or use the local development fallback in production.

## Release Commands

Run these commands from the `WMS` directory as part of a release or one-off deployment task:

```powershell
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

The Django project is in the repository's `WMS` subdirectory. If the hosting
service starts in the repository root (as Render does when its Root Directory
is blank), set its start command to:

```text
gunicorn --chdir WMS WMS.wsgi:application --bind 0.0.0.0:$PORT
```

Alternatively, set the service Root Directory to `WMS` and use
`gunicorn WMS.wsgi:application --bind 0.0.0.0:$PORT`.

Configure the platform's health check to request `/`. Create the first privileged account with `python manage.py createsuperuser`. Do not run `seed_demo_data` in production; the command refuses to create its known-password demonstration users when `DEBUG` is disabled.

## Before Opening Traffic

- Verify `check --deploy` is clean with the real host, database, SMTP, and proxy environment.
- Confirm the public domain and HTTPS certificate, then test login, logout, CSRF-protected form submissions, and static assets through the public hostname.
- Confirm the PostgreSQL backup/restore process and set up database monitoring and error reporting.
- Replace optional contact fields with approved business details.
- Keep `DJANGO_DEBUG=false`; do not expose the local SQLite database or development credentials.
