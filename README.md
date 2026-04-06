# Finance Data Processing and Access Control Backend

## Overview
F
A Django REST backend for secure financial record management, role-based access control, and dashboard analytics.

The system supports JWT authentication, user roles, transaction CRUD, and financial summary reports. It works locally with SQLite and can run in production with PostgreSQL and Redis.

## Tech Stack
- Python 3.11
- Django 4.2
- Django REST Framework
- PostgreSQL (production)
- SQLite (development)
- Redis (optional caching)
- drf-spectacular for API docs
- pytest / pytest-django

## Requirements
- Python 3.11+
- Git
- Optional: PostgreSQL, Redis, Docker

## Local Setup
1. Clone the repository:
```bash
git clone https://github.com/anshumankashyap/fintrackOS.git
cd finance_backend
```
2. Create and activate a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Copy `.env.example` to `.env` and update values as needed.
5. Run database migrations:
```bash
python manage.py migrate
```
6. Create an admin user:
```bash
python manage.py shell < scripts/seed_admin.py
```

### Default Admin Credentials
- Email: `admin@finance.local`
- Password: `AdminSeed123!`

> Change the password immediately after first login.

7. Start the server:
```bash
python manage.py runserver
```

## Environment Variables
Use `.env.example` as the reference. Key variables:
- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `DATABASE_URL`
- `REDIS_URL`
- `CACHE_TTL`
- `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`
- `JWT_REFRESH_TOKEN_LIFETIME_DAYS`
- `CORS_ALLOWED_ORIGINS`
- `DJANGO_SETTINGS_MODULE`

## API Base URL
`/api/v1/`

### Auth
- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/token/refresh/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/me/`
- `PUT /api/v1/auth/me/`
- `POST /api/v1/auth/change-password/`
- `GET /api/v1/auth/users/` (admin only)
- `GET /api/v1/auth/users/{uuid}/` (admin only)

### Records
- `GET /api/v1/records/`
- `POST /api/v1/records/`
- `GET /api/v1/records/{uuid}/`
- `PUT /api/v1/records/{uuid}/`
- `PATCH /api/v1/records/{uuid}/`
- `DELETE /api/v1/records/{uuid}/`

### Dashboard
- `GET /api/v1/dashboard/summary/`
- `GET /api/v1/dashboard/monthly-report/`
- `GET /api/v1/dashboard/weekly-report/`
- `GET /api/v1/dashboard/recent-activity/`

## Access Control
- `viewer` — read-only dashboard access
- `analyst` — read own records and dashboard data
- `admin` — full record CRUD and user management

## Validation Rules
- Amount must be positive
- Title is required and must be at least 3 characters
- Category must be a valid choice
- Transaction date cannot be in the future or older than 10 years
- Expense records above 10,000 require a description

## Database
- Custom `User` model with UUID primary key and role field
- `FinancialRecord` model captures amount, category, transaction type, description, date, and owner
- Local development defaults to SQLite
- Production supports PostgreSQL with Redis cache fallback

## Running Tests
```bash
pytest -q
```

## Optional Docker
If you need a containerized setup, use `docker-compose.yml` with PostgreSQL and Redis.

```bash
docker-compose up -d
```

Seed the admin user if needed:
```bash
docker-compose exec app python scripts/seed_admin.py
```

## API Documentation
- Swagger: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI schema: `/api/schema/`

## Notes
- Docker and Redis are optional for local development.
- The primary focus is secure backend API behavior and RBAC enforcement.
