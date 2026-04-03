"""
scripts/seed_admin.py
──────────────────────
One-time seed script: creates a default Admin user.

Usage (inside the container or local venv):
    python scripts/seed_admin.py

Or via manage.py shell:
    python manage.py shell < scripts/seed_admin.py
"""

import os
import sys
import django

# Bootstrap Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_backend.settings.development")
django.setup()

from accounts.models import Role, User
from django.contrib.auth import get_user_model

User = get_user_model()

ADMIN_EMAIL    = os.environ.get("SEED_ADMIN_EMAIL",    "admin@finance.local")
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "AdminSeed123!")

if User.objects.filter(email=ADMIN_EMAIL).exists():
    print(f"ℹ️  Admin user already exists: {ADMIN_EMAIL}")
else:
    User.objects.create_superuser(
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD,
        first_name="System",
        last_name="Admin",
    )
    print(f"✅ Admin user created: {ADMIN_EMAIL}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print("   ⚠️  Change this password immediately after first login!")
