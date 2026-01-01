# Easy Auth Redirect Fix

## Problem

When visiting `/login` on Azure, it shows the local login form instead of redirecting to Microsoft login.

## Root Cause

The code checks for Easy Auth headers (`X-MS-CLIENT-PRINCIPAL-ID`), but these headers only exist **AFTER** a user has been authenticated. On first visit to `/login`, the user isn't authenticated yet, so no headers exist, and the code falls back to local authentication.

## Solution

Updated the code to:
1. **Check if running on Azure** (using `WEBSITE_INSTANCE_ID` environment variable)
2. **If on Azure**, always redirect to Easy Auth login (`.auth/login/aad`)
3. **If local**, use local authentication

## Azure Portal Settings

Your current settings:
- **Restrict access**: Require authentication
- **Unauthenticated requests**: Return HTTP 401 Unauthorized

**This setting blocks requests before they reach your Flask app!**

### Recommended Change

Change to:
- **Action to take when request is not authenticated**: **"Allow anonymous requests (no action)"**

**Why?**
- Allows unauthenticated users to reach `/login`
- Your code can then redirect to Easy Auth
- Supports both Easy Auth and local auth fallback

## Steps to Fix

### 1. Update Azure Portal Settings

1. Go to Azure Portal → Your App → **Authentication**
2. Click **"Edit"** next to "Authentication settings"
3. Change **"Action to take when request is not authenticated"** to:
   - ✅ **"Allow anonymous requests (no action)"**
4. Click **"Save"**

### 2. Redeploy Code

The code has been updated to automatically redirect to Easy Auth when on Azure. Redeploy your app:

```bash
git add .
git commit -m "Fix Easy Auth redirect on Azure"
git push
```

### 3. Test

1. **Wait 1-2 minutes** for deployment
2. **Go to**: `https://fieldforce-dashboard.azurewebsites.net/login`
3. **Should redirect** to Microsoft login page
4. **After login**, should redirect back to dashboard

## How It Works Now

### On Azure (Production)

```
User visits /login
    ↓
Code detects WEBSITE_INSTANCE_ID exists
    ↓
Redirects to /.auth/login/aad
    ↓
Microsoft login page
    ↓
User authenticates
    ↓
Redirects to /auth/easy-auth-callback
    ↓
System maps user to organization/role
    ↓
Generates JWT token
    ↓
Redirects to dashboard
```

### Local (Development)

```
User visits /login
    ↓
Code detects no WEBSITE_INSTANCE_ID
    ↓
Shows local login form
    ↓
User enters username/password
    ↓
Generates JWT token
    ↓
Redirects to dashboard
```

## Verification

After deploying, check:

1. **Visit** `https://fieldforce-dashboard.azurewebsites.net/login`
2. **Should redirect** to Microsoft login (not show local form)
3. **After login**, should see dashboard with correct role

## Troubleshooting

### Still seeing local login form?

1. **Check Azure Portal settings** - Must be "Allow anonymous requests"
2. **Verify code is deployed** - Check deployment logs
3. **Check environment variable** - `WEBSITE_INSTANCE_ID` should exist on Azure
4. **Clear browser cache** - Hard refresh (Ctrl+F5)

### Getting 401 errors?

- Azure is blocking requests
- Change setting to "Allow anonymous requests"
- Or configure redirect URI in App Registration

### Redirect loop?

- Check redirect URI is configured in App Registration
- Must be: `https://fieldforce-dashboard.azurewebsites.net/.auth/login/aad/callback`

