#!/usr/bin/env python3
"""Test script to verify user persistence in database."""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from forge.storage.user import get_user_store
from forge.storage.data_models.user import User
from forge.server.middleware.auth import UserRole
from forge.server.utils.password import hash_password


async def test_user_persistence():
    """Test that users persist in the database."""
    print("=" * 80)
    print("Testing User Persistence in PostgreSQL")
    print("=" * 80)
    
    # Get database connection info
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "forge")
    user = os.getenv("DB_USER", "forge")
    password = os.getenv("DB_PASSWORD", "forge")
    
    print(f"\nDatabase Configuration:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")
    print(f"  User: {user}")
    
    # Connect directly to database to check current state
    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        conn = await asyncpg.connect(dsn)
        
        # Check current user count
        count_before = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"\nCurrent users in database: {count_before}")
        
        # List existing users
        if count_before > 0:
            users = await conn.fetch("SELECT id, email, username, created_at FROM users ORDER BY created_at DESC LIMIT 5")
            print("\nExisting users:")
            for u in users:
                print(f"  - {u['email']} ({u['username']}) - Created: {u['created_at']}")
        
        await conn.close()
        
        # Now test creating a user through the user store
        print("\n" + "=" * 80)
        print("Testing User Store")
        print("=" * 80)
        
        user_store = get_user_store()
        print(f"User store type: {type(user_store).__name__}")
        
        # Create a test user
        test_email = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}@test.com"
        test_username = f"testuser_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        print(f"\nCreating test user:")
        print(f"  Email: {test_email}")
        print(f"  Username: {test_username}")
        
        test_user = User(
            email=test_email,
            username=test_username,
            password_hash=hash_password("testpassword123"),
            role=UserRole.USER,
            email_verified=False,
            is_active=True,
        )
        
        created_user = await user_store.create_user(test_user)
        print(f"  User ID: {created_user.id}")
        print(f"  [OK] User created successfully")
        
        # Verify user exists immediately
        print("\nVerifying user exists immediately after creation...")
        conn = await asyncpg.connect(dsn)
        count_after = await conn.fetchval("SELECT COUNT(*) FROM users")
        user_in_db = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            created_user.id
        )
        await conn.close()
        
        if user_in_db:
            print(f"  [OK] User found in database")
            print(f"  Total users now: {count_after}")
        else:
            print(f"  [ERROR] User NOT found in database!")
            print(f"  This indicates the INSERT was not committed!")
            return False
        
        # Wait a moment
        print("\nWaiting 2 seconds...")
        await asyncio.sleep(2)
        
        # Verify user still exists
        print("Verifying user still exists after 2 seconds...")
        conn = await asyncpg.connect(dsn)
        user_still_exists = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            created_user.id
        )
        await conn.close()
        
        if user_still_exists:
            print(f"  [OK] User still exists in database")
        else:
            print(f"  [ERROR] User disappeared from database!")
            return False
        
        # Clean up test user
        print(f"\nCleaning up test user...")
        deleted = await user_store.delete_user(created_user.id)
        if deleted:
            print(f"  [OK] Test user deleted")
        else:
            print(f"  [WARNING] Could not delete test user (may not exist)")
        
        print("\n" + "=" * 80)
        print("[OK] Test completed successfully!")
        print("=" * 80)
        print("\nIf users are disappearing after restart, check:")
        print("  1. Database connection settings are consistent")
        print("  2. No database reset/cleanup scripts are running")
        print("  3. Database is not being recreated on startup")
        print("  4. Connection pool is not using a different database")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_user_persistence())
    sys.exit(0 if success else 1)

