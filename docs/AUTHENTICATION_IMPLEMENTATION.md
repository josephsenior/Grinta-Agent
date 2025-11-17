# Authentication System Implementation

## Overview

A complete user authentication and authorization system has been implemented for the Forge AI agent platform. This includes user registration, login, password management, JWT-based authentication, and user management capabilities.

## Features Implemented

### 1. User Registration & Login
- **POST `/api/auth/register`** - Register new user accounts
  - Email and username validation
  - Password strength requirements
  - Automatic JWT token generation
  - Duplicate email/username prevention

- **POST `/api/auth/login`** - Authenticate users
  - Email/password authentication
  - Account lockout after failed attempts
  - JWT token generation
  - Last login tracking

- **POST `/api/auth/logout`** - Logout (client-side token discard)

- **POST `/api/auth/refresh`** - Refresh authentication token

### 2. Password Management
- **POST `/api/auth/change-password`** - Change password (authenticated users)
- **POST `/api/auth/forgot-password`** - Request password reset
- **POST `/api/auth/reset-password`** - Reset password with token

### 3. User Profile
- **GET `/api/auth/me`** - Get current user information

### 4. User Management (Admin)
- **GET `/api/users`** - List all users (admin only, paginated)
- **GET `/api/users/{user_id}`** - Get user by ID (admin or own account)
- **PATCH `/api/users/{user_id}`** - Update user (admin or own account with restrictions)
- **DELETE `/api/users/{user_id}`** - Delete user (admin only)

## Security Features

### Password Security
- **Bcrypt hashing** with configurable rounds (default: 12)
- **Password strength validation**:
  - Minimum 8 characters
  - Must contain uppercase and lowercase letters
  - Must contain at least one digit
  - Maximum 128 characters

### Account Protection
- **Account lockout** after failed login attempts (configurable, default: 5 attempts)
- **Lockout duration** (configurable, default: 30 minutes)
- **Account deactivation** support
- **Email verification** support (structure in place)

### JWT Authentication
- **Token-based authentication** using JWT
- **Configurable expiration** (default: 24 hours)
- **Role-based access control** (admin, user, service)
- **Token refresh** mechanism

## Architecture

### Data Models

#### User Model (`forge/storage/data_models/user.py`)
```python
- id: str (UUID)
- email: str
- username: str
- password_hash: str (bcrypt)
- role: UserRole (admin, user, service)
- email_verified: bool
- is_active: bool
- created_at: datetime
- updated_at: datetime
- last_login: Optional[datetime]
- failed_login_attempts: int
- locked_until: Optional[datetime]
```

### Storage

#### FileUserStore (`forge/storage/user/file_user_store.py`)
- File-based user storage (JSON)
- Stores users in `.forge/users/users.json`
- In-memory cache for performance
- Configurable storage path via `USER_STORAGE_PATH` environment variable

**Future**: Can be extended to support database backends (PostgreSQL, MongoDB, etc.)

### Middleware

#### AuthMiddleware (`forge/server/middleware/auth.py`)
- JWT token verification
- User authentication enforcement
- Role-based access control
- Public endpoint exclusion
- Optional user active status verification

**Configuration**:
- `AUTH_ENABLED`: Enable/disable authentication (default: false)
- `AUTH_VERIFY_USER_ACTIVE`: Verify user is active on each request (default: true)
- `JWT_SECRET`: Secret key for JWT signing
- `JWT_EXPIRATION_HOURS`: Token expiration time (default: 24)

### Utilities

#### Password Utilities (`forge/server/utils/password.py`)
- `hash_password()`: Bcrypt password hashing
- `verify_password()`: Password verification
- `is_password_strong()`: Password strength validation

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login user |
| POST | `/api/auth/logout` | Yes | Logout user |
| POST | `/api/auth/refresh` | Yes | Refresh token |
| GET | `/api/auth/me` | Yes | Get current user |
| POST | `/api/auth/change-password` | Yes | Change password |
| POST | `/api/auth/forgot-password` | No | Request password reset |
| POST | `/api/auth/reset-password` | No | Reset password |

### User Management Endpoints

| Method | Endpoint | Auth Required | Role Required | Description |
|--------|----------|---------------|---------------|-------------|
| GET | `/api/users` | Yes | Admin | List users |
| GET | `/api/users/{id}` | Yes | Admin or Own | Get user |
| PATCH | `/api/users/{id}` | Yes | Admin or Own | Update user |
| DELETE | `/api/users/{id}` | Yes | Admin | Delete user |

## Configuration

### Environment Variables

```bash
# Authentication
AUTH_ENABLED=true                    # Enable authentication middleware
AUTH_VERIFY_USER_ACTIVE=true         # Verify user active status on each request
JWT_SECRET=your-secret-key           # JWT signing secret
JWT_EXPIRATION_HOURS=24              # Token expiration in hours
JWT_ALGORITHM=HS256                  # JWT algorithm

# User Storage
USER_STORAGE_PATH=.forge/users       # Path to user storage directory

# Security
MAX_LOGIN_ATTEMPTS=5                 # Max failed login attempts before lockout
ACCOUNT_LOCKOUT_MINUTES=30           # Lockout duration in minutes
```

## Usage Examples

### Register a User

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "SecurePass123"
  }'
```

Response:
```json
{
  "status": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "username": "johndoe",
      "role": "user",
      ...
    },
    "expires_in": 86400
  }
}
```

### Login

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

### Authenticated Request

```bash
curl -X GET http://localhost:3000/api/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Integration with Existing System

### UserAuth Implementation

A new `AuthenticatedUserAuth` class (`forge/server/user_auth/authenticated_user_auth.py`) has been created that integrates with the JWT authentication system. This can be used by setting:

```python
server_config.user_auth_class = "forge.server.user_auth.authenticated_user_auth.AuthenticatedUserAuth"
```

### Middleware Integration

The authentication middleware is automatically enabled when `AUTH_ENABLED=true` is set. It:
- Validates JWT tokens on protected endpoints
- Sets `request.state.user_id`, `request.state.user_email`, and `request.state.user_role`
- Excludes public endpoints from authentication

## Security Considerations

1. **Password Storage**: Passwords are hashed using bcrypt with 12 rounds
2. **Token Security**: JWT tokens are signed with a secret key (must be set in production)
3. **Account Lockout**: Prevents brute-force attacks
4. **Email Enumeration**: Password reset endpoint doesn't reveal if email exists
5. **Role-Based Access**: Admin-only endpoints are protected
6. **Input Validation**: All inputs are validated using Pydantic models

## Future Enhancements

1. **Email Verification**: Implement email verification flow
2. **OAuth Integration**: Add OAuth2/OpenID Connect support
3. **Two-Factor Authentication**: Add 2FA support
4. **Session Management**: Add session tracking and management
5. **Password Reset Email**: Implement email sending for password resets
6. **Database Backend**: Add PostgreSQL/MongoDB user store implementations
7. **Rate Limiting**: Add rate limiting to auth endpoints
8. **Audit Logging**: Add comprehensive audit logging

## Files Created/Modified

### New Files
- `forge/storage/data_models/user.py` - User data model
- `forge/storage/user/user_store.py` - User storage abstraction
- `forge/storage/user/file_user_store.py` - File-based user storage
- `forge/server/utils/password.py` - Password utilities
- `forge/server/routes/auth.py` - Authentication routes
- `forge/server/routes/user_management.py` - User management routes
- `forge/server/user_auth/authenticated_user_auth.py` - Authenticated UserAuth implementation

### Modified Files
- `forge/server/middleware/auth.py` - Added user verification, public paths
- `forge/server/app.py` - Added auth and user management routers
- `pyproject.toml` - Added bcrypt dependency

## Testing

To test the authentication system:

1. **Enable authentication**:
   ```bash
   export AUTH_ENABLED=true
   export JWT_SECRET=your-secret-key-here
   ```

2. **Start the server**:
   ```bash
   python -m forge.server
   ```

3. **Register a user**:
   ```bash
   curl -X POST http://localhost:3000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "username": "testuser", "password": "Test1234"}'
   ```

4. **Login**:
   ```bash
   curl -X POST http://localhost:3000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "Test1234"}'
   ```

5. **Use the token**:
   ```bash
   curl -X GET http://localhost:3000/api/auth/me \
     -H "Authorization: Bearer YOUR_TOKEN_HERE"
   ```

## Notes

- The file-based storage is suitable for development and small deployments
- For production, consider implementing a database-backed user store
- Password reset tokens are stored in-memory (use Redis in production)
- Email sending for password resets is not yet implemented (TODO in code)
- The system is designed to be extensible for additional authentication methods

