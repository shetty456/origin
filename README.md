# Origin — Internal Product Platform

Origin is a modular Django monolith — the shared backend foundation for all products we build.

**Goal:** For any future product, create a Django app under `products/`, add only product-specific models and APIs, connect a frontend, and ship.

---

## Philosophy

- **DRY** — Cross-product functionality belongs in core.
- **YAGNI** — Don't implement before a real requirement exists.
- **KISS** — Boring Django solutions over clever infrastructure.
- **Modular** — A product should be removable without breaking others.

---

## Repository structure

```
origin/
├── backend/
│   ├── manage.py
│   ├── config/               # Django project config & settings
│   ├── core/                 # Platform primitives
│   │   ├── identity/         # User ↔ Identity (multi-provider auth)
│   │   ├── users/            # User model
│   │   ├── organizations/    # Org + Membership
│   │   ├── permissions/      # Permission primitives
│   │   └── observability/    # Request IDs, structured logging
│   ├── products/             # Product apps live here
│   └── requirements/
├── docs/
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Local setup

```bash
git clone https://github.com/shetty456/origin.git
cd origin
cp .env.example .env
make build
make migrate
make createsuperuser
```

Then visit `http://localhost:8000/admin`.

---

## Common commands

| Command | What it does |
|---|---|
| `make up` | Start all services |
| `make build` | Rebuild and start |
| `make down` | Stop all services |
| `make migrate` | Run migrations |
| `make makemigrations` | Create migrations (use `app=<name>`) |
| `make shell` | Django shell |
| `make createsuperuser` | Create admin user |
| `make test` | Run tests |
| `make logs` | Tail web logs |
| `make psql` | Connect to PostgreSQL |

---

## Environment variables

See `.env.example` for all required variables. Never commit `.env`.

---

## Creating a new product

See [docs/new-product.md](docs/new-product.md).

---

## Architecture

See [docs/architecture.md](docs/architecture.md).

---

## Tech stack

- Python 3.12
- Django 4.2
- Django REST Framework
- PostgreSQL 16
- Docker + Docker Compose
- Railway (production)
