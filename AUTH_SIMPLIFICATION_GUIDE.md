# Authentication Simplification Guide

## Current State

Your project has **TWO** authentication systems running in parallel:

### 1. Token-Based Auth (What You Want) ✅
- **Environment variable:** `SESSION_API_KEY`
- **Location:** `backend/runtime/action_execution_server.py`
- **How it works:** Set `SESSION_API_KEY=your_token` and all API requests need `X-Session-API-Key` header
- **Perfect for OSS:** Simple, no database, no user accounts

### 2. User/Password Auth (What You DON'T Want) ❌
- **Files involved:**
  - `backend/server/middleware/auth.py` - User authentication middleware
  - `backend/server/utils/password.py` - bcrypt password hashing
  - `backend/storage/user/` - User storage (database + file-based)
  - `backend/storage/data_models/user.py` - User model with password_hash
- **What it does:** Full user management with login, password hashing, roles, sessions

## Why You're Frustrated

You have bcrypt, password hashing, user storage, and all this complexity **when you just want a simple API token**. This is common in projects that evolved from "quick prototype" → "enterprise features" → "wait, we don't need this for OSS".

## How to Simplify (If You Want)

### Option A: Keep Both (Current State)
- Token auth for API access
- User auth disabled/unused
- **Pro:** Nothing breaks
- **Con:** Dead code sitting around

### Option B: Rip Out User Auth (Nuclear Option)
**Files to delete:**
```bash
rm backend/server/utils/password.py
rm backend/storage/user/database_user_store.py
rm backend/storage/user/file_user_store.py
rm backend/storage/data_models/user.py
```

**Middleware to remove:**
- In `backend/server/middleware/auth.py`, keep only the token validation parts
- Remove `UserRole`, `User` model, password checking

**Dependencies to remove from `pyproject.toml`:**
```toml
bcrypt = "^4.3.0"  # <-- Delete this line
```

### Option C: Document It and Move On (Recommended)
Add this to your README:

```markdown
## Authentication

Forge uses **token-based authentication**. No user accounts or passwords needed.

Set your API token:
```bash
export SESSION_API_KEY=your_secret_token_here
```

All API requests must include:
```
X-Session-API-Key: your_secret_token_here
```

---

**Note:** The codebase contains legacy user/password authentication code that is not used in OSS deployments. It can be safely ignored.
```

## What I Recommend

**For now:** Do nothing. The token auth works, the password stuff doesn't interfere. 

**Later:** If it really bothers you, do a cleanup sprint:
1. Create a git branch: `git checkout -b remove-user-auth`
2. Delete the files listed in Option B
3. Test extensively
4. Merge when ready

## Quick Wins You Already Have

✅ Token-based auth is already implemented  
✅ No forced login flow  
✅ OSS-friendly architecture  
✅ The password code is isolated and not in your way  

---

## TL;DR

You're right to be annoyed. The token-based auth (`SESSION_API_KEY`) is what you need and it works. The user/password system is legacy code that got committed but isn't active in your workflow. It's harmless but clutters the codebase.

**Do this now:** Just ignore the user auth files and use `SESSION_API_KEY`. 
**Do this later:** Clean it up in a dedicated PR when you have time.
