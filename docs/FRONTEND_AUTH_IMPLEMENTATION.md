# Frontend Authentication Implementation

## Overview

Complete frontend authentication system integrated with the Forge AI agent platform. This includes user registration, login, password management, JWT token handling, route protection, and admin user management.

## Features Implemented

### 1. Authentication Pages
- **Login Page** (`/auth/login`) - User login with email/password
- **Register Page** (`/auth/register`) - New user registration
- **Forgot Password** (`/auth/forgot-password`) - Password reset request
- **Reset Password** (`/auth/reset-password`) - Password reset with token

### 2. User Profile
- **Profile Page** (`/profile`) - User profile with auth integration
  - Shows username, email, role
  - Displays admin badge for admin users
  - Quick actions for settings

### 3. Admin Features
- **User Management** (`/admin/users`) - Admin-only user management dashboard
  - List all users with pagination
  - Search users
  - View user details
  - Edit/delete users (admin only)

### 4. Route Protection
- **AuthGuard Component** - Protects routes requiring authentication
- **Role-based Access** - Admin-only routes protected
- **Automatic Redirects** - Unauthenticated users redirected to login

### 5. User Menu Integration
- **Header User Menu** - Updated to show:
  - Username and email from auth context
  - Admin badge for admin users
  - Admin Panel link (admin only)
  - Logout functionality

## File Structure

```
frontend/src/
├── api/
│   ├── auth.ts                    # Authentication API client
│   └── users.ts                   # User management API client
│
├── components/
│   └── features/
│       └── auth/
│           └── auth-guard.tsx     # Route protection component
│
├── context/
│   └── auth-context.tsx           # Auth context provider
│
├── hooks/
│   ├── auth/
│   │   ├── use-login.ts          # Login mutation hook
│   │   ├── use-register.ts       # Register mutation hook
│   │   ├── use-logout.ts         # Logout mutation hook
│   │   ├── use-password-reset.ts # Password reset hooks
│   │   └── use-user-profile.ts   # User profile query hook
│   └── query/
│       └── use-users.ts          # User management hooks
│
├── routes/
│   ├── auth/
│   │   ├── login.tsx             # Login page
│   │   ├── register.tsx          # Registration page
│   │   ├── forgot-password.tsx   # Password reset request
│   │   └── reset-password.tsx    # Password reset confirmation
│   ├── admin/
│   │   └── users.tsx             # User management (admin)
│   ├── dashboard.tsx             # Protected dashboard
│   └── profile.tsx               # Protected profile page
│
├── types/
│   └── auth.ts                   # Auth TypeScript types
│
└── utils/
    └── auth/
        ├── token-storage.ts      # Token storage utilities
        ├── token-refresh.ts      # Automatic token refresh
        └── permissions.ts        # Role-based permissions
```

## Key Components

### AuthContext (`context/auth-context.tsx`)
- Global authentication state management
- Provides `user`, `isAuthenticated`, `isLoading`, `error`
- Methods: `login()`, `register()`, `logout()`, `refreshUser()`
- Automatically initializes from localStorage on mount
- Sets up automatic token refresh

### AuthGuard (`components/features/auth/auth-guard.tsx`)
- Protects routes requiring authentication
- Supports role-based access control
- Shows loading state while checking auth
- Redirects unauthenticated users to login

### UserProfileDropdown (`components/features/user/user-profile-dropdown.tsx`)
- Updated to use auth context
- Shows username, email, and role
- Displays admin badge
- Includes admin panel link for admins
- Integrated logout functionality

## API Integration

### Authentication API (`api/auth.ts`)
```typescript
- register(data: RegisterRequest): Promise<LoginResponse>
- login(data: LoginRequest): Promise<LoginResponse>
- logout(): Promise<void>
- getCurrentUser(): Promise<User>
- refreshToken(): Promise<{token, expires_in}>
- changePassword(data: ChangePasswordRequest): Promise<void>
- forgotPassword(data: ForgotPasswordRequest): Promise<void>
- resetPassword(data: ResetPasswordRequest): Promise<void>
```

### User Management API (`api/users.ts`)
```typescript
- listUsers(page, limit): Promise<PaginatedUsersResponse>
- getUserById(userId): Promise<User>
- updateUser(userId, data): Promise<User>
- deleteUser(userId): Promise<void>
```

## Token Management

### Automatic Token Handling
- **Storage**: Tokens stored in localStorage
- **Injection**: Automatically added to API requests via axios interceptor
- **Refresh**: Automatic token refresh 5 minutes before expiration
- **Cleanup**: Tokens cleared on logout or 401 errors

### Axios Interceptor (`api/forge-axios.ts`)
- **Request Interceptor**: Adds `Authorization: Bearer <token>` header
- **Response Interceptor**: Handles 401 errors by clearing tokens and redirecting to login

## Route Protection

### Protected Routes
Routes wrapped with `<AuthGuard>`:
- `/dashboard` - Requires authentication
- `/profile` - Requires authentication
- `/admin/users` - Requires admin role

### Public Routes
- `/auth/login` - Login page
- `/auth/register` - Registration page
- `/auth/forgot-password` - Password reset request
- `/auth/reset-password` - Password reset confirmation
- `/` - Home/landing page

## Usage Examples

### Using Auth Context
```typescript
import { useAuth } from '#/context/auth-context';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth();
  
  if (!isAuthenticated) {
    return <div>Please login</div>;
  }
  
  return <div>Welcome, {user?.username}!</div>;
}
```

### Protecting a Route
```typescript
import { AuthGuard } from '#/components/features/auth/auth-guard';

export default function ProtectedPage() {
  return (
    <AuthGuard>
      <div>Protected content</div>
    </AuthGuard>
  );
}
```

### Admin-Only Route
```typescript
<AuthGuard requireRole="admin">
  <AdminPanel />
</AuthGuard>
```

### Using Auth Hooks
```typescript
import { useLogin } from '#/hooks/auth/use-login';

function LoginForm() {
  const loginMutation = useLogin();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await loginMutation.mutateAsync({ email, password });
      // Redirect handled automatically
    } catch (error) {
      // Handle error
    }
  };
}
```

## Integration Points

### Root Layout (`entry.client.tsx`)
- `AuthProvider` wraps the entire app
- Provides auth context to all components

### Routes Configuration (`routes.ts`)
- Auth routes added as public routes
- Admin routes added with proper structure

### Header Component
- `UserProfileDropdown` updated to use auth context
- Shows user info and logout option

## Security Features

1. **Token Storage**: Secure localStorage with automatic cleanup
2. **Token Refresh**: Automatic refresh before expiration
3. **Route Protection**: Client-side route guards
4. **Role-Based Access**: Admin-only features protected
5. **401 Handling**: Automatic logout on token expiration
6. **Input Validation**: Form validation on all auth pages

## Next Steps (Optional Enhancements)

1. **Email Verification UI** - When backend email verification is implemented
2. **Two-Factor Authentication** - Add 2FA UI components
3. **Session Management** - Show active sessions and ability to revoke
4. **User Edit Modal** - Inline editing in admin users table
5. **Bulk User Operations** - Select multiple users for bulk actions
6. **User Activity Logs** - Show user activity history
7. **Password Strength Indicator** - Visual feedback during password entry

## Testing

To test the authentication system:

1. **Start the backend** with `AUTH_ENABLED=true`:
   ```bash
   export AUTH_ENABLED=true
   export JWT_SECRET=your-secret-key
   python -m forge.server
   ```

2. **Start the frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test Flow**:
   - Navigate to `/auth/register` to create an account
   - Login at `/auth/login`
   - Access protected routes like `/dashboard` or `/profile`
   - Test logout from user menu
   - Test password reset flow
   - Test admin user management (requires admin role)

## Notes

- The authentication system works alongside existing auth mechanisms
- Token-based authentication is stateless (JWT)
- All auth state is managed through React Context
- Automatic token refresh prevents session expiration
- Route protection happens client-side (backend also validates)
- Admin features are conditionally rendered based on user role

