# Azure App Service Easy Auth Integration Guide

## Overview

This application now supports **Azure App Service Easy Auth** (built-in authentication) while maintaining:
- ✅ User management (add/remove/edit users)
- ✅ Multiple organizations support
- ✅ Custom JWT tokens with organization/role fields
- ✅ RBAC (Role-Based Access Control) for dashboards and features

## Architecture

### Hybrid Authentication System

The application uses a **hybrid authentication approach**:

1. **Easy Auth** (when enabled): Handles OAuth flow with identity providers (Microsoft Entra, Google, etc.)
2. **Local Auth** (fallback): Username/password authentication stored in `users.json`
3. **Custom JWT Tokens**: Generated after Easy Auth authentication to include organization/role information

### How It Works

```
┌─────────────────┐
│  User Requests  │
│  /login         │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Easy Auth Enabled?     │
│  (Check headers)        │
└─────┬───────────┬───────┘
      │           │
   YES│           │NO
      │           │
      ▼           ▼
┌──────────┐  ┌──────────────┐
│ Easy Auth│  │ Local Auth   │
│ OAuth    │  │ (username/    │
│ Flow     │  │  password)    │
└────┬─────┘  └──────┬───────┘
     │               │
     ▼               ▼
┌─────────────────────────┐
│  Extract User Identity  │
│  (from Easy Auth headers)│
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Map to Organization/   │
│  Role (user_mappings.json)│
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Generate Custom JWT    │
│  (with org/role)        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Set JWT Cookie        │
│  Redirect to Dashboard │
└────────────────────────┘
```

## Setup Instructions

### Step 1: Enable Easy Auth in Azure Portal

#### 1.1 Navigate to Your Web App

1. Go to [Azure Portal](https://portal.azure.com)
2. Sign in with your Azure account
3. Search for your **App Service** (Web App) in the search bar
4. Click on your web app name to open it

#### 1.2 Open Authentication Settings

1. In the left sidebar, scroll down to **Settings** section
2. Click on **Authentication**
3. You'll see the Authentication page with options to add identity providers

#### 1.3 Add Microsoft Identity Provider

1. Click the **Add identity provider** button (or **+ Add** button)
2. In the **Identity provider** dropdown, select **Microsoft**
3. You'll see two options:
   - **Create new app registration** (Recommended for first time)
   - **Pick an existing app registration in this directory**

#### 1.4 Configure App Registration (If Creating New)

If you selected **Create new app registration**:

1. **Name**: Enter a name for your app registration (e.g., "Dashboard-App-Auth")
2. **Supported account types**: Choose one:
   - **Accounts in this organizational directory only** - Only users in your Azure AD tenant
   - **Accounts in any organizational directory** - Users from any Azure AD tenant
   - **Accounts in any organizational directory and personal Microsoft accounts** - Any Microsoft account
3. **Rest API permissions** (Optional): Click **Add a permission** if you need to access Microsoft Graph API
4. Click **Add** at the bottom

#### 1.5 Use Existing App Registration (If Selected)

If you selected **Pick an existing app registration**:

1. Select your app registration from the dropdown
2. Click **Add**

### Step 2: Configure Authentication Settings

After adding the identity provider, configure the authentication behavior:

1. In the **Authentication** page, click on **Authentication settings** (or the **Edit** button next to it)
2. Configure the following:

   **Action to take when request is not authenticated**:
   - **Allow anonymous requests (no action)** ✅ **RECOMMENDED**
     - This allows both Easy Auth and local authentication to work
     - Users can choose how to authenticate
   - **Sign in with Microsoft** 
     - Forces all users to use Easy Auth
     - Blocks local authentication

3. **Token store** (Optional):
   - Enable if you need to access provider tokens (e.g., Microsoft Graph API)
   - Usually not needed for basic authentication

4. Click **Save**

### Step 3: Configure Redirect URIs in Microsoft Entra ID

After creating the app registration, you need to configure the redirect URI:

#### 3.1 Open App Registration

1. In Azure Portal, search for **Microsoft Entra ID** (or **Azure Active Directory**)
2. Click on **App registrations** in the left sidebar
3. Find your app registration (the name you used in Step 1.4)
4. Click on it to open

#### 3.2 Add Redirect URI

1. In the left sidebar, click on **Authentication**
2. Under **Platform configurations**, you'll see **Web** platform (or click **+ Add a platform** and select **Web**)
3. In the **Redirect URIs** section, click **+ Add URI**
4. Add the following redirect URI:
   ```
   https://YOUR-APP-NAME.azurewebsites.net/.auth/login/aad/callback
   ```
   Replace `YOUR-APP-NAME` with your actual Azure Web App name
   
   Example:
   ```
   https://my-dashboard-app.azurewebsites.net/.auth/login/aad/callback
   ```

5. If you have a custom domain, also add:
   ```
   https://YOUR-CUSTOM-DOMAIN/.auth/login/aad/callback
   ```

6. Under **Implicit grant and hybrid flows**, check:
   - ✅ **ID tokens** (usually checked by default)

7. Click **Save**

#### 3.3 Verify Redirect URI Format

The redirect URI must match exactly:
- Protocol: `https://` (not `http://`)
- Domain: Your Azure Web App domain or custom domain
- Path: `/.auth/login/aad/callback` (exact path, case-sensitive)

### Step 4: Test the Configuration

1. **Save all changes** in Azure Portal
2. Wait 1-2 minutes for changes to propagate
3. Navigate to your web app URL: `https://YOUR-APP-NAME.azurewebsites.net/login`
4. You should be redirected to Microsoft login page
5. After logging in, you'll be redirected back to your app

### Step 5: Map Users to Organizations

After Easy Auth is working, map users to organizations:

1. Log in as a **Dachido admin** (using local auth if needed)
2. Navigate to `/admin/users` in your app
3. Click **Map Easy Auth User**
4. Enter:
   - Easy Auth User ID (from Azure headers)
   - Organization
   - Username
   - Role
5. Save the mapping

### Troubleshooting Setup

#### Issue: Redirect URI Mismatch Error

**Error**: "AADSTS50011: The redirect URI specified in the request does not match the redirect URIs configured for the application"

**Solution**:
1. Check the redirect URI in App Registration matches exactly
2. Ensure you're using `https://` not `http://`
3. Verify the domain matches your web app URL
4. The path must be exactly `/.auth/login/aad/callback`

#### Issue: Easy Auth Not Redirecting

**Symptoms**: Login page shows local auth form instead of redirecting

**Solution**:
1. Check that Authentication is enabled in Azure Portal
2. Verify the identity provider is added and saved
3. Check browser console for errors
4. Try clearing browser cache and cookies
5. Verify the web app is running (not stopped)

#### Issue: User Not Found After Login

**Symptoms**: User logs in via Easy Auth but gets "User not mapped" error

**Solution**:
1. Go to `/admin/users` as Dachido admin
2. Map the Easy Auth user to an organization
3. Or ensure the user's email matches an email in `users.json` for automatic mapping

### Quick Reference: Azure Portal Paths

```
Azure Portal
└── App Services
    └── YOUR-WEB-APP
        └── Settings
            └── Authentication  ← Step 1 & 2

Azure Portal
└── Microsoft Entra ID
    └── App registrations
        └── YOUR-APP-REGISTRATION
            └── Authentication  ← Step 3
```

### 4. Environment Variables

No additional environment variables needed! The system automatically detects Easy Auth by checking for Easy Auth headers.

## User Management

### Mapping Easy Auth Users to Organizations

When a user first logs in via Easy Auth, they need to be mapped to an organization and role:

1. **Automatic Mapping** (if email matches):
   - If the Easy Auth email matches an email in `users.json`, the system automatically creates a mapping

2. **Manual Mapping** (Dachido admin):
   - Dachido admins can map Easy Auth users via `/admin/users`
   - Go to User Management page
   - Click "Map Easy Auth User"
   - Select organization, username, and role

### User Mapping Storage

Mappings are stored in `user_mappings.json`:
```json
{
  "easy_auth_id:abc123": {
    "organization": "coromandel",
    "role": "admin",
    "username": "admin",
    "easy_auth_id": "abc123",
    "email": "user@example.com"
  },
  "email:user@example.com": {
    "organization": "coromandel",
    "role": "admin",
    "username": "admin",
    "easy_auth_id": "abc123",
    "email": "user@example.com"
  }
}
```

## API Endpoints

### User Management (Dachido Admin Only)

- `GET /api/users` - List all users
- `POST /api/users` - Create new user
- `PUT /api/users/<user_key>` - Update user
- `DELETE /api/users/<user_key>` - Delete user

### Authentication

- `GET /login` - Login page (redirects to Easy Auth if enabled)
- `GET /auth/easy-auth-callback` - Easy Auth callback handler
- `GET /auth/map-user` - Map Easy Auth user to organization (Dachido admin)
- `GET /logout` - Logout

## RBAC (Role-Based Access Control)

### Available Roles

1. **dachido_admin**: Full access, can manage all organizations
2. **admin**: Organization admin, can manage users in their organization
3. **customer_admin**: Limited access, view-only for most features

### Using RBAC Decorators

```python
from auth import login_required, require_role, require_dachido_admin, has_permission

# Require any authenticated user
@app.route("/dashboard")
@login_required
def dashboard():
    pass

# Require specific role
@app.route("/admin/users")
@login_required
@require_role('dachido_admin', 'admin')
def manage_users():
    pass

# Require Dachido admin
@app.route("/admin/settings")
@login_required
@require_dachido_admin
def admin_settings():
    pass

# Check permission
if has_permission('manage_users'):
    # Show user management UI
    pass
```

### Permission System

Permissions are defined in `auth.py`:

```python
permissions = {
    'dachido_admin': ['*'],  # All permissions
    'admin': ['view_dashboard', 'manage_users', 'view_analytics', 'manage_recordings'],
    'customer_admin': ['view_dashboard', 'view_analytics', 'view_recordings']
}
```

## Development vs Production

### Local Development

- Easy Auth is **not available** locally
- System automatically falls back to local authentication
- Use username/password from `users.json`

### Production (Azure)

- Easy Auth is **automatically detected** via headers
- If Easy Auth is enabled, login redirects to OAuth provider
- If Easy Auth is disabled, falls back to local auth

## Files Created/Modified

### New Files

- `easy_auth.py` - Easy Auth integration module
- `user_mappings.json` - Maps Easy Auth identities to organizations/roles
- `AZURE_EASY_AUTH_INTEGRATION.md` - This documentation

### Modified Files

- `auth.py` - Added Easy Auth support, RBAC helpers
- `app.py` - Added user management routes, Easy Auth callback

## Troubleshooting

### Easy Auth Not Working

1. **Check headers**: Verify `X-MS-CLIENT-PRINCIPAL-ID` header is present
2. **Check Azure Portal**: Ensure Authentication is enabled
3. **Check redirect URI**: Verify callback URL is configured correctly

### User Not Mapped

1. Check `user_mappings.json` for existing mapping
2. Use `/admin/users` to manually map user
3. Verify email matches if using automatic mapping

### JWT Token Issues

1. Check `JWT_SECRET_KEY` environment variable
2. Verify token expiration (30 minutes default)
3. Check cookie settings (secure flag, httponly, samesite)

## Security Considerations

1. **JWT Secret Key**: Must be set via `JWT_SECRET_KEY` environment variable in production
2. **HTTPS**: Always use HTTPS in production (Easy Auth enforces this)
3. **Cookie Security**: Cookies are HTTP-only, secure, and SameSite=Lax
4. **Token Expiration**: Tokens expire after 30 minutes
5. **Role Validation**: Always validate roles on the server side

## Next Steps

1. **Enable Easy Auth** in Azure Portal
2. **Test login flow** with Microsoft Entra ID
3. **Map users** to organizations via `/admin/users`
4. **Configure RBAC** for your specific use case
5. **Add more identity providers** if needed (Google, Facebook, etc.)

## Support

For issues or questions:
- Check Azure App Service logs for Easy Auth errors
- Review `user_mappings.json` for mapping issues
- Verify JWT token payload in browser DevTools

