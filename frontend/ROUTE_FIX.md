# Fixing React Router v7 Route 404 Issues

If you're experiencing 404 errors for routes that are correctly defined in `routes.ts`, follow these steps:

## Quick Fix

1. **Stop your dev server** (Ctrl+C)

2. **Clear the React Router cache and regenerate routes:**
   ```bash
   npm run rebuild-routes
   ```

3. **Restart your dev server:**
   ```bash
   npm run dev
   ```

## Manual Steps

If the quick fix doesn't work:

1. **Clear cache manually:**
   ```bash
   npm run clear-routes
   ```

2. **Regenerate route types:**
   ```bash
   react-router typegen
   ```

3. **Restart dev server:**
   ```bash
   npm run dev
   ```

## Why This Happens

React Router v7 caches route manifests for performance. When you add new routes, the cache may not update automatically, causing 404 errors even though the route is correctly defined.

## Prevention

After adding new routes, always run:
```bash
npm run rebuild-routes
```

This ensures the route manifest is regenerated and the cache is cleared.

