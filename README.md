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
│   ├── config/                  # Django project config & settings
│   │   ├── settings/
│   │   │   ├── base.py          # Shared settings
│   │   │   ├── dev.py           # Local overrides
│   │   │   └── prod.py          # Production overrides
│   │   ├── urls.py              # Root URL conf (admin, API, docs)
│   │   └── api_urls.py          # /api/v1/ router
│   ├── core/                    # Platform primitives
│   │   ├── users/               # Custom User model
│   │   ├── identity/            # Multi-provider auth (OTP, OAuth)
│   │   └── organizations/       # Org + Membership
│   ├── products/                # Product apps live here
│   └── requirements/
├── docs/
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Core modules

### `core.users`

The platform `User` model. Intentionally minimal — no product-specific fields here.

| Field | Notes |
|-------|-------|
| `id` | UUID primary key |
| `name` | Display name |
| `email` | Nullable, unique — used for Django admin login only |
| `is_active` / `is_staff` | Standard Django flags |

Authentication proper goes through `core.identity`, not this model.

---

### `core.identity`

Multi-provider identity system. A single user can have multiple identities (email, phone, Google, Apple). Each provider has its own `Identity` row.

**Models:**

`Identity`

| Field | Notes |
|-------|-------|
| `user` | FK to User |
| `provider` | `email` / `phone` / `google` / `apple` |
| `identifier` | Email address, E.164 phone number, OAuth subject ID, etc. |
| `verified_at` | Null until the identity is confirmed |
| `metadata` | JSON — stores OAuth tokens, profile info, etc. |

`OTPRequest`

| Field | Notes |
|-------|-------|
| `identity` | FK to Identity |
| `otp_hash` | SHA-256 of the OTP — never stored in plaintext |
| `expires_at` | 10 minutes from creation |
| `attempts` | Incremented atomically on each wrong guess |
| `verified_at` | Set atomically on correct verification |

**OTP rules:**
- 4-digit numeric code (`0000`–`9999`)
- Expires after **10 minutes**
- Max **5 wrong attempts** before lockout
- **60-second cooldown** between resend requests
- OTP is marked used via a conditional atomic DB update — two concurrent correct submissions cannot both succeed

---

### `core.organizations`

Multi-tenant organization support.

| Model | Key fields |
|-------|-----------|
| `Organization` | `id` (UUID), `name`, `slug`, `is_active` |
| `Membership` | `user`, `organization`, `role` (`owner` / `admin` / `member`) |

---

## API

Interactive docs are available at **`/api/docs/`** (Swagger UI) and **`/api/redoc/`** (ReDoc) when the server is running.

All endpoints are prefixed `/api/v1/auth/`.

---

### Authentication

Sign up and log in via email or phone OTP. Successful verification returns a JWT token pair.

#### `POST /api/v1/auth/otp/email/request/`

Request an OTP to the given email. Creates a user if one does not exist.

**Request**
```json
{ "email": "user@example.com" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "detail": "OTP sent." }` |
| `400` | Validation error |
| `429` | `{ "detail": "Please wait before requesting another OTP." }` |

---

#### `POST /api/v1/auth/otp/email/verify/`

Verify the email OTP and receive JWT tokens.

**Request**
```json
{ "email": "user@example.com", "otp": "3821" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "access": "<jwt>", "refresh": "<jwt>" }` |
| `400` | Invalid or expired OTP |

---

#### `POST /api/v1/auth/otp/phone/request/`

Request an OTP to the given phone number (E.164 format). Creates a user if one does not exist.

**Request**
```json
{ "phone": "+919876543210" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "detail": "OTP sent." }` |
| `400` | Validation error |
| `429` | `{ "detail": "Please wait before requesting another OTP." }` |

---

#### `POST /api/v1/auth/otp/phone/verify/`

Verify the phone OTP and receive JWT tokens.

**Request**
```json
{ "phone": "+919876543210", "otp": "3821" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "access": "<jwt>", "refresh": "<jwt>" }` |
| `400` | Invalid or expired OTP |

---

### Token

#### `POST /api/v1/auth/token/refresh/`

Refresh an access token. Refresh tokens rotate on every use.

**Request**
```json
{ "refresh": "<refresh_jwt>" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "access": "<jwt>", "refresh": "<jwt>" }` |
| `401` | Token invalid or expired |

Token lifetimes: access **60 minutes**, refresh **7 days**.

---

### Identity

Link additional email or phone identities to an already-authenticated account. All endpoints require a `Bearer` token.

#### `POST /api/v1/auth/identity/link/email/request/`

Send an OTP to an email to link it to the authenticated user's account.

**Request**
```json
{ "email": "other@example.com" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "detail": "OTP sent." }` |
| `400` | Validation error |
| `401` | Authentication required |
| `409` | Email already linked to an account |
| `429` | Cooldown active |

---

#### `POST /api/v1/auth/identity/link/email/verify/`

Verify the OTP and complete the email link.

**Request**
```json
{ "email": "other@example.com", "otp": "5047" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "detail": "Email linked successfully." }` |
| `400` | Invalid or expired OTP |
| `401` | Authentication required |

---

#### `POST /api/v1/auth/identity/link/phone/request/`

Send an OTP to a phone number to link it to the authenticated user's account.

**Request**
```json
{ "phone": "+919876543210" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "detail": "OTP sent." }` |
| `400` | Validation error |
| `401` | Authentication required |
| `409` | Phone already linked to an account |
| `429` | Cooldown active |

---

#### `POST /api/v1/auth/identity/link/phone/verify/`

Verify the OTP and complete the phone link.

**Request**
```json
{ "phone": "+919876543210", "otp": "5047" }
```

**Responses**

| Status | Body |
|--------|------|
| `200` | `{ "detail": "Phone linked successfully." }` |
| `400` | Invalid or expired OTP |
| `401` | Authentication required |

---

## Admin

Visit `http://localhost:8000/admin/` after running `make createsuperuser`.

Notable admin features:
- **Users** — lists email, name, phone number (pulled from phone Identity), status, and timestamps. Searchable by email, name, or phone number.
- **Identities** — view all provider–identifier pairs and their verification status.
- **OTP Requests** — inspect OTP state, attempt counts, expiry, and verification timestamps.
- **Organizations / Memberships** — manage orgs and member roles.

---

## Local setup

**Prerequisites:** Docker and Docker Compose.

```bash
git clone https://github.com/shetty456/origin.git
cd origin
cp .env.example .env
make build
make migrate
make createsuperuser
```

Then visit:
- `http://localhost:8000/admin/` — Django admin
- `http://localhost:8000/api/docs/` — Swagger UI
- `http://localhost:8000/api/redoc/` — ReDoc

---

## Common commands

| Command | What it does |
|---------|-------------|
| `make up` | Start all services |
| `make build` | Rebuild images and start |
| `make down` | Stop all services |
| `make restart` | Stop then start |
| `make migrate` | Run pending migrations |
| `make makemigrations app=<name>` | Create migrations for an app |
| `make shell` | Django shell |
| `make createsuperuser` | Create an admin user |
| `make test` | Run tests |
| `make logs` | Tail web container logs |
| `make psql` | Connect to PostgreSQL |

---

## Environment variables

Copy `.env.example` to `.env` and adjust as needed. Never commit `.env`.

| Variable | Default | Notes |
|----------|---------|-------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | Use `config.settings.prod` in production |
| `DJANGO_SECRET_KEY` | — | **Required.** Use a long random string in production |
| `DEBUG` | `True` | Set to `False` in production |
| `DB_NAME` | `origin` | |
| `DB_USER` | `origin` | |
| `DB_PASSWORD` | `origin` | |
| `DB_HOST` | `db` | Docker service name |
| `DB_PORT` | `5432` | |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated |

---

## Creating a new product

See [docs/new-product.md](docs/new-product.md).

---

## Architecture

See [docs/architecture.md](docs/architecture.md).

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Framework | Django 4.2 + Django REST Framework |
| Auth | simplejwt (JWT) + custom OTP flow |
| API docs | drf-spectacular (Swagger / ReDoc) |
| Database | PostgreSQL 16 |
| Containers | Docker + Docker Compose |
| Production | Railway |
