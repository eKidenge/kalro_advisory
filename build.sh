#!/usr/bin/env bash
# ==================================================================
# KALRO Advisory — Render build script
# Safe to run repeatedly. Idempotent.
# ==================================================================
set -o errexit   # exit on error
set -o pipefail  # catch pipe errors

echo "🚀 Starting KALRO Advisory build..."

# ------------------------------------------------------------------
# 1. Install dependencies
# ------------------------------------------------------------------
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# ------------------------------------------------------------------
# 2. Apply migrations
#    NEVER delete existing migration files — they are your schema.
# ------------------------------------------------------------------
echo "🗄️  Applying migrations..."
python manage.py migrate --noinput

# ------------------------------------------------------------------
# 3. Collect static files
# ------------------------------------------------------------------
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

# ------------------------------------------------------------------
# 4. Idempotent superuser creation
#    Only creates if it doesn't already exist.
# ------------------------------------------------------------------
echo "👤 Ensuring superuser exists..."
python manage.py shell << 'PYEOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@kalro.go.ke')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if not password:
    print('⚠️  DJANGO_SUPERUSER_PASSWORD not set — skipping superuser creation.')
else:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'role': 'SYS_ADMIN',
            'is_staff': True,
            'is_superuser': True,
            'is_verified': True,
        },
    )
    if created:
        user.set_password(password)
        user.save()
        print(f'✅ Superuser created: {username}')
    else:
        # Make sure flags are set even if user already existed
        changed = False
        if not user.is_staff:
            user.is_staff = True; changed = True
        if not user.is_superuser:
            user.is_superuser = True; changed = True
        if password:
            user.set_password(password); changed = True
        if changed:
            user.save()
            print(f'✅ Superuser {username} updated.')
        else:
            print(f'ℹ️  Superuser {username} already exists — no changes.')
PYEOF

echo "✅ Build completed successfully."