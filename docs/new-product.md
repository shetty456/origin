# Creating a New Product on Origin

## Overview

A product is a Django app that lives under `backend/products/<product-name>/`. It uses Origin's core for auth, users, organizations, and observability — it only defines what makes it unique.

## Steps

### 1. Create the app

```bash
cd backend
python manage.py startapp <product-name> products/<product-name>
```

### 2. Register the app

Add to `INSTALLED_APPS` in `config/settings/base.py`:

```python
LOCAL_APPS = [
    ...
    "products.<product-name>",
]
```

### 3. Set the app label in `apps.py`

```python
class MyProductConfig(AppConfig):
    name = "products.my_product"
    label = "my_product"
```

### 4. Define product models

In `products/<product-name>/models.py` — reference core models via FK:

```python
from core.users.models import User

class MyModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ...
```

### 5. Create and run migrations

```bash
make makemigrations app=products.<product-name>
make migrate
```

### 6. Create serializers, views, URLs

Standard DRF patterns. Mount URLs in `config/api_urls.py`:

```python
path("my-product/", include("products.my_product.urls")),
```

### 7. Add permissions

Use Origin's permission primitives from `core.permissions`.

### 8. Write tests

In `products/<product-name>/tests/`.

### 9. Ship

The product is ready. Core handles auth, users, logging, and request IDs automatically.

## What you never need to build per-product

- Authentication system
- User model or user creation
- Organization primitives
- Request ID / structured logging
- Error handling conventions
- API response format
