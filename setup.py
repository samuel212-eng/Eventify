#!/usr/bin/env python3
"""
Run this script once to set up the Eventify database and create a superuser.
Usage:  python setup.py
"""
import os
import sys
import subprocess

def run(cmd):
    """Run a terminal command and show the output"""
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"ERROR: command failed → {cmd}")
        sys.exit(1)

print("=" * 50)
print("  Eventify Setup")
print("=" * 50)

# 1. Install dependencies
print("\n[1/4] Installing Django and Pillow (for image uploads)...")
run("pip install django pillow")

# 2. Create database tables from our models
print("\n[2/4] Creating database tables...")
run("python manage.py makemigrations")
run("python manage.py migrate")

# 3. Add some sample categories
print("\n[3/4] Adding sample categories...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventsite.settings')
import django
django.setup()
from events.models import Category
for name in ['Music', 'Technology', 'Sports', 'Art & Culture', 'Food & Drink', 'Networking']:
    Category.objects.get_or_create(name=name)
    print(f"   ✓ Category: {name}")

# 4. Create admin user
print("\n[4/4] Creating admin superuser...")
print("   (You'll use this to log into /admin)")
run("python manage.py createsuperuser")

print("\n" + "=" * 50)
print("  Setup complete! 🎉")
print("  Run the site:  python manage.py runserver")
print("  Then visit:    http://127.0.0.1:8000")
print("=" * 50)
