# Origin — Architecture

## Overview

Origin is a modular Django monolith — a single deployable backend that serves as the shared foundation for all products.

## Core vs Product

```
backend/
├── core/          ← platform primitives (auth, users, orgs, permissions, observability)
└── products/      ← product-specific apps (quiz/, tutor/, etc.)
```

Core owns: authentication, users, organizations, permissions, observability infrastructure.
Products own: product models, serializers, views, URLs, business logic, tests.

Core must never import from products. Products may import from core.

## Identity model

```
User
 └── Identity (provider, identifier, verified_at, metadata)
```

A User can have multiple Identities across providers (email, phone, Google, Apple, SSO). This allows authentication to evolve without changing the User model.

## Authentication

Token-based REST authentication. OTP flows (email/phone) supported. Architecture leaves clean extension points for OAuth providers.

## B2B model

```
User → Membership → Organization
```

A user may belong to multiple organizations with different roles. B2C products are not required to use organizations.

## API structure

```
/api/v1/<product-or-core-resource>/
```

## Deployment

Railway (initial). Docker Compose for local development.

## Diagrams

_To be added as the system evolves._
