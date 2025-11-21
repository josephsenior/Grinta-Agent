# GitHub OAuth Setup Guide

This guide explains how to configure GitHub OAuth for the "Continue with GitHub" button on the registration/login pages.

## Required Environment Variables

The GitHub OAuth integration requires the following environment variables:

```bash
GITHUB_CLIENT_ID=your_github_client_id
# OR
GITHUB_APP_CLIENT_ID=your_github_client_id

GITHUB_CLIENT_SECRET=your_github_client_secret
```

## Where to Set These Variables

### Option 1: System Environment Variables (Recommended for Development)

**Windows (PowerShell):**
```powershell
$env:GITHUB_CLIENT_ID="your_client_id"
$env:GITHUB_CLIENT_SECRET="your_client_secret"
```

**Windows (Command Prompt):**
```cmd
set GITHUB_CLIENT_ID=your_client_id
set GITHUB_CLIENT_SECRET=your_client_secret
```

**macOS/Linux:**
```bash
export GITHUB_CLIENT_ID="your_client_id"
export GITHUB_CLIENT_SECRET="your_client_secret"
```

### Option 2: Create a `.env` File (Recommended for Local Development)

Create a `.env` file in the project root directory:

```bash
# .env file in project root
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

**Note:** Make sure `.env` is in your `.gitignore` to avoid committing secrets!

### Option 3: Set in Your Shell Profile (Persistent)

**Windows (PowerShell Profile):**
```powershell
# Edit: $PROFILE
[System.Environment]::SetEnvironmentVariable('GITHUB_CLIENT_ID', 'your_client_id', 'User')
[System.Environment]::SetEnvironmentVariable('GITHUB_CLIENT_SECRET', 'your_client_secret', 'User')
```

**macOS/Linux (~/.bashrc or ~/.zshrc):**
```bash
export GITHUB_CLIENT_ID="your_client_id"
export GITHUB_CLIENT_SECRET="your_client_secret"
```

## How to Get GitHub OAuth Credentials

1. **Go to GitHub Settings:**
   - Visit: https://github.com/settings/developers
   - Or: GitHub → Settings → Developer settings → OAuth Apps

2. **Create a New OAuth App:**
   - Click "New OAuth App"
   - Fill in the form:
     - **Application name**: Forge (or your app name)
     - **Homepage URL**: `http://localhost:3000` (for development)
     - **Authorization callback URL**: `http://localhost:3000/api/auth/oauth/github/callback`
   - Click "Register application"

3. **Get Your Credentials:**
   - **Client ID**: Shown on the app page (public)
   - **Client Secret**: Click "Generate a new client secret" (keep this secret!)

4. **For Production:**
   - Update the callback URL to your production domain:
     - `https://yourdomain.com/api/auth/oauth/github/callback`
   - Update the homepage URL to your production domain

## Verify Configuration

After setting the environment variables, restart your Forge server and check:

1. **Check if variables are loaded:**
   ```bash
   # In Python
   python -c "import os; print('GITHUB_CLIENT_ID:', os.getenv('GITHUB_CLIENT_ID', 'NOT SET'))"
   ```

2. **Test the OAuth flow:**
   - Go to the registration page
   - Click "Continue with GitHub"
   - You should be redirected to GitHub for authorization
   - After authorizing, you should be redirected back to your app

## Troubleshooting

### "GitHub OAuth not configured" Error

- **Check environment variables are set:**
  ```bash
  # Windows PowerShell
  $env:GITHUB_CLIENT_ID
  $env:GITHUB_CLIENT_SECRET
  ```

- **Restart the server** after setting environment variables
- **Check the callback URL** matches exactly what you set in GitHub

### "Invalid redirect_uri" Error

- The callback URL in your GitHub OAuth app must match exactly:
  - Development: `http://localhost:3000/api/auth/oauth/github/callback`
  - Production: `https://yourdomain.com/api/auth/oauth/github/callback`

### OAuth Works But User Creation Fails

- Check server logs for errors
- Verify the user store is properly configured
- Check that email retrieval from GitHub is working

## Current Configuration Status

Based on the code, the system looks for:
- `GITHUB_CLIENT_ID` OR `GITHUB_APP_CLIENT_ID` (either works)
- `GITHUB_CLIENT_SECRET` (required)

The callback URL is automatically constructed as:
- `{base_url}/api/auth/oauth/github/callback`

Where `base_url` is determined from the incoming request.

## Security Notes

- **Never commit** `.env` files or environment variables to version control
- **Use different OAuth apps** for development and production
- **Rotate secrets** if they're ever exposed
- **Use environment-specific secrets** in production deployments

