#!/usr/bin/env python3
"""Script to list all users from the user store.

This script works with both file-based and database-based user storage.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from forge.storage.user import get_user_store
from forge.storage.data_models.user import User


async def list_users():
    """List all users from the user store."""
    try:
        user_store = get_user_store()
        
        # List all users (with a high limit to get all)
        users = await user_store.list_users(skip=0, limit=10000)
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"\nFound {len(users)} user(s):\n")
        print("-" * 120)
        print(f"{'ID':<38} {'Email':<30} {'Username':<20} {'Role':<10} {'Active':<8} {'Verified':<10} {'Created At':<20}")
        print("-" * 120)
        
        for user in users:
            created_str = user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "N/A"
            print(
                f"{user.id:<38} "
                f"{user.email:<30} "
                f"{user.username:<20} "
                f"{user.role.value:<10} "
                f"{'Yes' if user.is_active else 'No':<8} "
                f"{'Yes' if user.email_verified else 'No':<10} "
                f"{created_str:<20}"
            )
        
        print("-" * 120)
        print(f"\nTotal: {len(users)} user(s)")
        
        # Show additional details if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
            print("\nDetailed Information:")
            print("=" * 120)
            for user in users:
                print(f"\nUser ID: {user.id}")
                print(f"  Email: {user.email}")
                print(f"  Username: {user.username}")
                print(f"  Role: {user.role.value}")
                print(f"  Active: {user.is_active}")
                print(f"  Email Verified: {user.email_verified}")
                print(f"  Created At: {user.created_at}")
                print(f"  Updated At: {user.updated_at}")
                print(f"  Last Login: {user.last_login or 'Never'}")
                print(f"  Failed Login Attempts: {user.failed_login_attempts}")
                print(f"  Locked Until: {user.locked_until or 'Not locked'}")
                print("-" * 120)
    
    except Exception as e:
        print(f"Error listing users: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(list_users())

