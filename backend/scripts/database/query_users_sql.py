#!/usr/bin/env python3
"""Script to query users directly from PostgreSQL database using SQL.

This script connects directly to the database and runs SQL queries.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg


async def query_users_sql():
    """Query users directly from PostgreSQL."""
    try:
        # Get connection parameters from environment
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", "5432"))
        database = os.getenv("DB_NAME", "forge")
        user = os.getenv("DB_USER", "forge")
        password = os.getenv("DB_PASSWORD", "forge")
        
        # Build connection string
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        print(f"Connecting to database: {database}@{host}:{port}")
        
        # Connect to database
        conn = await asyncpg.connect(dsn)
        
        try:
            # Check if users table exists
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                )
                """
            )
            
            if not table_exists:
                print("\n[WARNING] The 'users' table does not exist in the database.")
                print("   You may need to run migrations first:")
                print("   python -m forge.storage.user.migrations.run_migrations")
                return
            
            # Get table structure
            print("\nUsers Table Structure:")
            columns = await conn.fetch(
                """
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position
                """
            )
            
            print(f"{'Column':<25} {'Type':<20} {'Nullable':<10} {'Default':<20}")
            print("-" * 75)
            for col in columns:
                default = (col['column_default'] or '')[:18]  # Truncate long defaults
                print(f"{col['column_name']:<25} {col['data_type']:<20} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL':<10} {default:<20}")
            
            # Count users
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            print(f"\nTotal Users: {user_count}\n")
            
            if user_count == 0:
                print("No users found in the database.")
                return
            
            # Query all users
            users = await conn.fetch(
                """
                SELECT 
                    id,
                    email,
                    username,
                    role,
                    email_verified,
                    is_active,
                    created_at,
                    updated_at,
                    last_login,
                    failed_login_attempts,
                    locked_until
                FROM users
                ORDER BY created_at DESC
                """
            )
            
            # Format data for display
            table_data = []
            for row in users:
                created_at = row['created_at'].strftime("%Y-%m-%d %H:%M:%S") if row['created_at'] else "N/A"
                updated_at = row['updated_at'].strftime("%Y-%m-%d %H:%M:%S") if row['updated_at'] else "N/A"
                last_login = row['last_login'].strftime("%Y-%m-%d %H:%M:%S") if row['last_login'] else "Never"
                locked_until = row['locked_until'].strftime("%Y-%m-%d %H:%M:%S") if row['locked_until'] else "Not locked"
                
                table_data.append([
                    str(row['id'])[:8] + "...",  # Truncate UUID for display
                    row['email'],
                    row['username'],
                    row['role'],
                    'Yes' if row['email_verified'] else 'No',
                    'Yes' if row['is_active'] else 'No',
                    created_at,
                    updated_at,
                    last_login,
                    row['failed_login_attempts'],
                    locked_until
                ])
            
            print("Users in Database:")
            headers = [
                'ID (truncated)',
                'Email',
                'Username',
                'Role',
                'Verified',
                'Active',
                'Created At',
                'Updated At',
                'Last Login',
                'Failed Logins',
                'Locked Until'
            ]
            col_widths = [12, 30, 20, 10, 8, 8, 19, 19, 19, 12, 19]
            
            # Print header
            header_row = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
            print(header_row)
            print("-" * len(header_row))
            
            # Print data rows
            for row in table_data:
                data_row = " | ".join(str(cell).ljust(w)[:w] for cell, w in zip(row, col_widths))
                print(data_row)
            
            # Show full UUIDs if requested
            if len(sys.argv) > 1 and sys.argv[1] == "--full-ids":
                print("\nFull User IDs:")
                for row in users:
                    print(f"  {row['email']}: {row['id']}")
        
        finally:
            await conn.close()
            print("\n[OK] Database connection closed.")
    
    except asyncpg.exceptions.InvalidPasswordError:
        print("[ERROR] Invalid database password.", file=sys.stderr)
        print("   Please check your DB_PASSWORD environment variable.", file=sys.stderr)
        sys.exit(1)
    except asyncpg.exceptions.ConnectionDoesNotExistError:
        print("[ERROR] Could not connect to database.", file=sys.stderr)
        print("   Please check your database connection settings:", file=sys.stderr)
        print(f"   DB_HOST={os.getenv('DB_HOST', 'localhost')}", file=sys.stderr)
        print(f"   DB_PORT={os.getenv('DB_PORT', '5432')}", file=sys.stderr)
        print(f"   DB_NAME={os.getenv('DB_NAME', 'forge')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(query_users_sql())

