#!/usr/bin/env python3
"""
Seed script to create initial admin and user accounts.

This script should be run once during initial deployment to create
the default admin and user accounts. The passwords should be changed
after first login in production.

Usage:
    python scripts/seed_users.py

Or from Docker:
    docker-compose exec app python scripts/seed_users.py
"""
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, engine
from app.db.base import Base
from app.models.user import User, UserRole
from app.core.security import get_password_hash


# Default users to seed
DEFAULT_USERS = [
    {
        "email": "admin@adkuu.com",
        "name": "Platform Admin",
        "password": "adm1n_s3cur3_k7x9!",
        "role": UserRole.ADMIN.value,
    },
    {
        "email": "andrei@adkuu.com",
        "name": "Andrei",
        "password": "us3r_acc3ss_m4p2!",
        "role": UserRole.USER.value,
    },
]


def seed_users():
    """Create default users if they don't exist."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        created_count = 0
        skipped_count = 0

        for user_data in DEFAULT_USERS:
            # Check if user already exists
            existing = db.query(User).filter(User.email == user_data["email"]).first()

            if existing:
                print(f"  [SKIP] User '{user_data['email']}' already exists (id={existing.id})")
                skipped_count += 1
                continue

            # Create new user
            user = User(
                email=user_data["email"],
                name=user_data["name"],
                password_hash=get_password_hash(user_data["password"]),
                role=user_data["role"],
                is_active=True,
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            print(f"  [CREATE] User '{user.email}' created with role '{user.role}' (id={user.id})")
            created_count += 1

        print(f"\nSeed complete: {created_count} created, {skipped_count} skipped")

        # Print login info
        print("\n" + "=" * 60)
        print("Default Credentials (CHANGE IN PRODUCTION!):")
        print("=" * 60)
        for user_data in DEFAULT_USERS:
            print(f"  {user_data['role'].upper()}:")
            print(f"    Email:    {user_data['email']}")
            print(f"    Password: {user_data['password']}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Error seeding users: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding default users...")
    print("-" * 40)
    seed_users()
