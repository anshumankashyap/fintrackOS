# 💰 Finance Data Processing & Access Control Backend

A **production-ready** Django REST Framework backend for storing and processing financial records with strict **Role-Based Access Control (RBAC)**.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Role-Based Access Control](#role-based-access-control)
5. [API Reference](#api-reference)
6. [Running Locally (Quick Start)](#running-locally-quick-start)
7. [Running with Docker](#running-with-docker)
8. [Running Tests](#running-tests)
9. [Deploying to Render](#deploying-to-render)
10. [Deploying to AWS EC2](#deploying-to-aws-ec2)
11. [Environment Variables Reference](#environment-variables-reference)
12. [Design Decisions](#design-decisions)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Client (HTTP)                       │
└──────────────────────────┬──────────────────────────────┘
                           │ Bearer JWT
┌──────────────────────────▼──────────────────────────────┐
│               Django REST Framework                     │
│                                                         │
│  ┌──────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ accounts │  │   records   │  │    dashboard     │   │
│  │          │  │             │  │                  │   │
│  │ Register │  │ CRUD APIs   │  │ /summary         │   │
│  │ Login    │  │ Filtering   │  │ /monthly-report  │   │
│  │ JWT auth │  │ Pagination  │  │                  │   │
│  │ User mgmt│  │             │  │ DashboardService │   │
│  └──────────┘  └─────────────┘  └──────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │         permissions/rbac.py  (RBAC layer)        │   │
│  │  IsAdmin | IsAnalystOrAbove | FinancialRecord     │   │
│  │          Permission matrix                       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              core/  (shared infrastructure)      │   │
│  │  exceptions | pagination | middleware | responses│   │
│  └──────────────────────────────────────────────────┘   │
└──────────────┬────────────────────────┬─────────────────┘
               │                        │
    ┌──────────▼────────┐    ┌──────────▼────────┐
    │   PostgreSQL 15    │    │     Redis 7        │
    │   (Primary store)  │    │  (Dashboard cache) │
    └───────────────────┘    └───────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4.2 + Django REST Framework 3.15 |
| Auth | JWT via `djangorestframework-simplejwt` |
| Database | PostgreSQL 15 |
| Caching | Redis 7 via `django-redis` |
| Filtering | `django-filter` |
| API Docs | `drf-spectacular` (Swagger + ReDoc) |
| CORS | `django-cors-headers` |
| Server | Gunicorn |
| Static files | WhiteNoise |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
finance_backend/
│
├── finance_backend/           # Django project package
│   ├── settings/
│   │   ├── base.py            # Shared settings (JWT, DRF, cache, logging)
│   │   ├── development.py     # Dev overrides (SQLite, debug, relaxed throttle)
│   │   └── production.py      # Prod overrides (SSL, hardened headers, SMTP)
│   ├── urls.py                # Root URL config + Swagger mounts
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/                  # Authentication & user management
│   ├── models.py              # Custom User model (UUID PK, email login, role)
│   ├── serializers.py         # Registration, profile, admin, JWT serializers
│   ├── views.py               # Register, login, logout, /me, admin CRUD
│   ├── urls.py
│   ├── admin.py
│   └── tests.py               # 30+ auth tests
│
├── records/                   # Financial records CRUD
│   ├── models.py              # FinancialRecord (UUID, Decimal amount, indexes)
│   ├── serializers.py         # Full + lightweight list serializers, validation
│   ├── filters.py             # FilterSet (category, type, date range, amount)
│   ├── views.py               # List/Create + Detail views with RBAC
│   ├── urls.py
│   ├── admin.py
│   └── tests.py               # Model, serializer, RBAC, filter tests
│
├── dashboard/                 # Financial analytics
│   ├── services.py            # DashboardService — pure business logic
│   ├── serializers.py         # Response shape serializers (dataclass → JSON)
│   ├── views.py               # /summary + /monthly-report with caching
│   ├── urls.py
│   └── tests.py               # Service unit tests + API tests
│
├── permissions/
│   └── rbac.py                # IsAdmin, IsAnalystOrAbove, FinancialRecordPermission
│
├── core/
│   ├── exceptions.py          # Global exception handler + custom error classes
│   ├── pagination.py          # StandardResultsPagination
│   ├── middleware.py          # Request logging middleware
│   └── responses.py           # success_response(), created_response() helpers
│
├── scripts/
│   ├── entrypoint.sh          # Docker: wait for PG → migrate → gunicorn
│   └── seed_admin.py          # Create first admin user
│
├── Dockerfile                 # Multi-stage production build
├── docker-compose.yml         # Full local stack (app + db + redis)
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md
```

---

## Role-Based Access Control

Three roles are enforced at the HTTP layer via DRF permission classes:

| Action | Viewer | Analyst | Admin |
|---|:---:|:---:|:---:|
| Read financial records | ✅ | ✅ | ✅ |
| Read dashboard summaries | ✅ | ✅ | ✅ |
| Create financial records | ❌ | ✅ | ✅ |
| Update financial records | ❌ | ✅ | ✅ |
| Delete financial records | ❌ | ❌ | ✅ |
| List all users | ❌ | ❌ | ✅ |
| Assign user roles | ❌ | ❌ | ✅ |
| Deactivate users | ❌ | ❌ | ✅ |

New users registered via `/api/v1/auth/register/` are always created as **Viewer**. An Admin must promote them.

---

## API Reference

All endpoints are prefixed with `/api/v1/`.
Interactive docs available at `/api/docs/` (Swagger UI) and `/api/redoc/`.

### Auth

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register/` | None | Register new user |
| POST | `/auth/login/` | None | Obtain JWT tokens |
| POST | `/auth/token/refresh/` | None | Refresh access token |
| POST | `/auth/logout/` | JWT | Blacklist refresh token |
| GET/PATCH | `/auth/me/` | JWT | View/update own profile |
| POST | `/auth/change-password/` | JWT | Change own password |
| GET | `/auth/users/` | Admin | List all users |
| GET/PATCH/DELETE | `/auth/users/{id}/` | Admin | Manage a user |

### Financial Records

| Method | Endpoint | Min Role | Description |
|---|---|---|---|
| GET | `/records/` | Viewer | List (paginated, filterable) |
| POST | `/records/` | Analyst | Create new record |
| GET | `/records/{id}/` | Viewer | Retrieve record |
| PUT/PATCH | `/records/{id}/` | Analyst | Update record |
| DELETE | `/records/{id}/` | Admin | Delete record |

**Filter parameters:** `?category=Rent&transaction_type=expense&date_from=2024-01-01&date_to=2024-12-31&amount_min=100&amount_max=5000&search=salary&ordering=-date`

### Dashboard

| Method | Endpoint | Min Role | Description |
|---|---|---|---|
| GET | `/dashboard/summary/` | Viewer | Totals + category breakdown |
| GET | `/dashboard/monthly-report/` | Viewer | Monthly income/expense trends |

**Parameters:** `?date_from=2024-01-01&date_to=2024-12-31&months=12`

### Example Responses

**POST /api/v1/auth/login/**
```json
{
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "alice@example.com",
    "full_name": "Alice Smith",
    "role": "analyst"
  }
}
```

**GET /api/v1/dashboard/summary/**
```json
{
  "success": true,
  "message": "Financial summary.",
  "data": {
    "total_income": "15000.00",
    "total_expense": "8500.00",
    "net_balance": "6500.00",
    "total_records": 42,
    "income_records": 18,
    "expense_records": 24,
    "is_profitable": true,
    "category_breakdown": [
      { "category": "Salary",    "total_income": "12000.00", "total_expense": "0.00",    "net": "12000.00", "record_count": 3 },
      { "category": "Rent",      "total_income": "0.00",     "total_expense": "4500.00", "net": "-4500.00", "record_count": 3 }
    ]
  }
}
```

**Error Response (any endpoint)**
```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "Input validation failed.",
  "errors": {
    "amount": ["Amount must be greater than zero."],
    "date":   ["Transaction date cannot be in the future."]
  }
}
```

---

## Running Locally (Quick Start)

### Prerequisites
- Python 3.11+
- PostgreSQL (or skip — SQLite is used automatically in dev mode)
- Redis (optional — dashboard caching degrades gracefully without it)

```bash
# 1. Clone and enter the project
git clone https://github.com/your-org/finance-backend.git
cd finance-backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and DB credentials

# 5. Apply database migrations
python manage.py migrate

# 6. Create an admin user
python scripts/seed_admin.py

# 7. Start the development server
python manage.py runserver

# API is now live at:  http://127.0.0.1:8000/
# Swagger UI:          http://127.0.0.1:8000/api/docs/
# Django Admin:        http://127.0.0.1:8000/admin/
```

> **SQLite by default:** In development mode, the app uses SQLite automatically (no PostgreSQL setup needed). Set `USE_POSTGRES=true` in your `.env` to switch to PostgreSQL locally.

---

## Running with Docker

```bash
# 1. Copy and configure environment
cp .env.example .env
# Fill in: SECRET_KEY, DB_PASSWORD, REDIS_PASSWORD, ALLOWED_HOSTS

# 2. Build and start all services (app + postgres + redis)
docker-compose up --build

# 3. (First run) Create admin user
docker-compose exec app python scripts/seed_admin.py

# Services:
#   App:      http://localhost:8000/
#   Swagger:  http://localhost:8000/api/docs/
#   PG:       localhost:5432
#   Redis:    localhost:6379
```

---

## Running Tests

```bash
# Run all tests
python manage.py test

# Or with pytest (more detailed output)
pytest

# Run a specific app's tests
pytest accounts/tests.py -v
pytest records/tests.py -v
pytest dashboard/tests.py -v

# With coverage report
coverage run -m pytest
coverage report -m
coverage html   # Opens in browser: htmlcov/index.html
```

---

## Deploying to Render

Render is the simplest zero-ops deployment path.

### Step 1 — Push to GitHub

```bash
git init && git add . && git commit -m "initial commit"
git remote add origin https://github.com/your-org/finance-backend.git
git push -u origin main
```

### Step 2 — Create Render services

1. Go to [render.com](https://render.com) → **New** → **PostgreSQL**
   - Note the **Internal Database URL**

2. **New** → **Redis** (optional but recommended)
   - Note the **Internal Redis URL**

3. **New** → **Web Service**
   - Connect your GitHub repo
   - **Runtime:** Docker
   - **Dockerfile path:** `./Dockerfile`
   - **Region:** nearest to your users

### Step 3 — Set environment variables in Render dashboard

```
SECRET_KEY            = (generate: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DEBUG                 = False
ALLOWED_HOSTS         = your-app.onrender.com
DATABASE_URL          = (paste Internal Database URL from step 2)
REDIS_URL             = (paste Internal Redis URL from step 2)
DJANGO_SETTINGS_MODULE= finance_backend.settings.production
```

### Step 4 — Deploy

Render auto-deploys on every push to `main`. The `entrypoint.sh` runs migrations on startup.

---

## Deploying to AWS EC2

### Step 1 — Launch an EC2 instance

- AMI: **Ubuntu 22.04 LTS**
- Instance type: `t3.small` or larger
- Security group inbound rules:
  - SSH (22) — your IP only
  - HTTP (80) — anywhere
  - HTTPS (443) — anywhere

### Step 2 — Connect and install Docker

```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin git
sudo usermod -aG docker ubuntu
newgrp docker
```

### Step 3 — Deploy the application

```bash
# Clone your repo
git clone https://github.com/your-org/finance-backend.git
cd finance-backend

# Configure environment
cp .env.example .env
nano .env    # Set all production values

# Build and start
docker compose up -d --build

# Seed admin
docker compose exec app python scripts/seed_admin.py
```

### Step 4 — Set up Nginx as a reverse proxy (optional but recommended)

```bash
sudo apt-get install -y nginx

sudo tee /etc/nginx/sites-available/finance-backend << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/finance-backend /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Step 5 — HTTPS via Let's Encrypt

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ | — | Django secret key (50+ random chars) |
| `DEBUG` | ✅ | `False` | Never `True` in production |
| `ALLOWED_HOSTS` | ✅ | — | Comma-separated hostnames |
| `DATABASE_URL` | ✅ | — | PostgreSQL connection URL |
| `REDIS_URL` | ✅ | — | Redis connection URL |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | ❌ | `60` | Access token TTL in minutes |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | ❌ | `7` | Refresh token TTL in days |
| `CORS_ALLOWED_ORIGINS` | ❌ | `http://localhost:3000` | Comma-separated frontend origins |
| `CACHE_TTL` | ❌ | `300` | Dashboard cache TTL in seconds |
| `DJANGO_SETTINGS_MODULE` | ✅ | — | `finance_backend.settings.production` |

---

## Design Decisions

### UUIDs as primary keys
All models use UUID primary keys. This prevents enumeration attacks (an attacker cannot guess `id=1, 2, 3...`) and makes IDs safe to expose in public URLs.

### Decimal for money, never Float
`amount` is stored as `DecimalField(max_digits=14, decimal_places=2)`. Floats introduce rounding errors (e.g. `0.1 + 0.2 ≠ 0.3`). This is unacceptable for financial data.

### Email as the login identifier
Username-based auth introduces a second identifier users must remember. Email is unique and already required — using it as the login field simplifies UX.

### Role in JWT payload
The user's role is embedded in the JWT access token. This means permission checks can be made without a database round-trip. If a role is revoked, the old access token remains valid until it expires (max 60 minutes). For immediate revocation, reduce `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`.

### Service layer for business logic
Dashboard calculations live in `DashboardService`, completely separate from views. This makes them independently testable with plain Python — no HTTP request needed. Views are thin: they authenticate, call the service, cache the result, and return the response.

### Graceful Redis degradation
The cache backend uses `IGNORE_EXCEPTIONS=True`. If Redis is unreachable, all cache operations silently no-op and the app continues to work — it just re-computes results on every request. This prevents a Redis outage from taking down the API.

### Custom exception handler
All errors — validation, auth, permission, 500 — are normalised to a single JSON envelope: `{ success, code, message, errors? }`. Frontend clients never have to handle different error shapes.
