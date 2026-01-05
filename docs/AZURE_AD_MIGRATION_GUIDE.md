# Migration Guide: Local Auth → Azure AD

## Overview

This guide walks you through migrating from local username/password authentication to Azure AD (Microsoft Entra ID) authentication with app roles for role-based access control.

---

## Step-by-Step Migration

### Phase 1: Azure AD Setup (1-2 hours)

#### 1. Create App Registration in Azure AD

1. **Go to Azure Portal**: https://portal.azure.com
2. **Navigate to Azure Active Directory** (or "Microsoft Entra ID")
3. **Click "App registrations"** in the left sidebar
4. **Click "New registration"**
5. **Fill in the form**:
   - **Name**: `FieldForce Dashboard` (or your app name)
   - **Supported account types**: 
     - ✅ **Accounts in this organizational directory only (Single tenant)** (recommended for security)
     - Or: **Accounts in any organizational directory** (if you need multi-tenant)
   - **Redirect URI**: 
     - Platform: **Web**
     - URI: `https://your-app-name.azurewebsites.net/auth/callback`
     - Replace `your-app-name` with your actual Azure App Service name
6. **Click "Register"**

#### 2. Configure App Registration

**A. Create Client Secret:**
1. In your App Registration, go to **"Certificates & secrets"**
2. Click **"New client secret"**
3. **Description**: `Dashboard Secret`
4. **Expires**: Choose expiration (24 months recommended)
5. **Click "Add"**
6. **⚠️ IMPORTANT**: Copy the **VALUE** immediately (you won't see it again!)
   - Save it securely (you'll need it for environment variables)

**B. Configure API Permissions:**
1. Go to **"API permissions"**
2. Click **"Add a permission"**
3. Select **"Microsoft Graph"**
4. Select **"Delegated permissions"**
5. Add these permissions:
   - ✅ `User.Read` (read user profile)
   - ✅ `email` (read user email)
   - ✅ `openid` (sign in)
   - ✅ `profile` (read user profile)
6. Click **"Add permissions"**
7. **Click "Grant admin consent for [Your Organization]"** (important!)

**C. Create App Roles:**
1. Go to **"App roles"** in the left sidebar
2. Click **"Create app role"**

   **Role 1: Dachido Admin**
   - **Display name**: `Dachido Admin`
   - **Allowed member types**: ✅ Users/Groups
   - **Value**: `dachido_admin`
   - **Description**: `Administrator for Dachido organization with full access`
   - Click **"Apply"**

   **Role 2: Customer Admin**
   - **Display name**: `Customer Admin`
   - **Allowed member types**: ✅ Users/Groups
   - **Value**: `customer_admin`
   - **Description**: `Administrator for customer organizations`
   - Click **"Apply"**

   **Role 3: Admin**
   - **Display name**: `Admin`
   - **Allowed member types**: ✅ Users/Groups
   - **Value**: `admin`
   - **Description**: `General administrator`
   - Click **"Apply"**

#### 3. Assign Users to Roles

1. **Go to Azure Active Directory** → **"Enterprise applications"**
2. **Find your app** (search by name: "FieldForce Dashboard")
3. Click on it
4. Go to **"Users and groups"** in the left sidebar
5. Click **"Add user/group"**
6. **Select users**:
   - Example: `dachido-admin@yourdomain.com` → Assign role: **"Dachido Admin"**
   - Example: `admin@coromandel.com` → Assign role: **"Admin"**
   - Example: `user@coromandel.com` → Assign role: **"Customer Admin"**
7. Click **"Assign"**

#### 4. Get Required IDs

From your App Registration page, copy these values (you'll need them for environment variables):
- **Application (client) ID** → `AZURE_CLIENT_ID`
- **Directory (tenant) ID** → `AZURE_TENANT_ID`
- **Client secret VALUE** (from step 2A) → `AZURE_CLIENT_SECRET`

---

### Phase 2: Code Changes (Already Done ✅)

The code has been updated with:
- ✅ `auth_azure.py` - Azure AD authentication module
- ✅ Updated `app.py` - Uses Azure AD authentication
- ✅ Updated `requirements.txt` - Added `msal` and `requests`

**No code changes needed!** Just configure environment variables.

---

### Phase 3: Environment Variables (15 minutes)

#### Set in Azure App Service:

1. **Go to Azure Portal** → Your App Service
2. **Settings** → **Configuration**
3. **Application settings** → **+ New application setting**

Add these settings:

```
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-value-here
AZURE_TENANT_ID=your-tenant-id-here
AZURE_REDIRECT_URI=https://your-app-name.azurewebsites.net/auth/callback
JWT_SECRET_KEY=generate-a-strong-random-key-here
```

**To generate JWT_SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

4. **Click "Save"**
5. **Restart your App Service** (Configuration → Overview → Restart)

#### For Local Development:

Create a `.env` file in your project root:
```env
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
AZURE_REDIRECT_URI=http://localhost:5000/auth/callback
JWT_SECRET_KEY=your-jwt-secret-key
```

---

### Phase 4: Testing (1 hour)

#### 1. Test Login Flow

1. **Deploy your code** (if not already deployed)
2. **Visit**: `https://your-app.azurewebsites.net/login`
3. **Should redirect** to Microsoft login page
4. **Enter email/password** of a user assigned to your app
5. **After login**, should redirect back to dashboard
6. **Check browser console** for success messages

#### 2. Test Role-Based Access

**As Dachido Admin:**
- ✅ Should access all sections
- ✅ Should see "User Management" tab
- ✅ Should access all organizations' data

**As Customer Admin:**
- ✅ Should access dashboard
- ✅ Should see only their organization's data
- ❌ Should NOT see "User Management" tab
- ❌ Should NOT access other organizations' data

**As Admin:**
- ✅ Should access dashboard
- ✅ Should see their organization's data
- ❌ Should NOT see "User Management" tab

#### 3. Test Token Persistence

1. **Login**
2. **Close browser**
3. **Reopen app**
4. **Should still be logged in** (until token expires - 8 hours)

---

### Phase 5: Cleanup (Optional - 15 minutes)

#### Remove Old Authentication Files

The following files are no longer needed (but kept for reference):
- `auth.py` - Old local authentication (can be archived)
- `easy_auth.py` - Easy Auth integration (can be archived)
- `users.json` - Local user storage (can be archived)
- `organizations.json` - Still used for display names (keep it)

**Note**: `organizations.json` is still used for organization display names, so keep it.

---

## User Management Going Forward

### Adding New Users

**Previously (Local Auth):**
```json
{
    "organization:username": {
        "password": "$2b$12$...",
        "role": "admin",
        ...
    }
}
```

**Now (Azure AD):**

1. **Add user to Azure AD:**
   - Azure Portal → **Azure Active Directory** → **Users**
   - Click **"New user"** → **"Create new user"**
   - Fill in:
     - **User principal name**: `user@yourdomain.com`
     - **Display name**: `User Name`
     - **Password**: Auto-generate or set password
   - Click **"Create"**

2. **Assign role to user:**
   - Azure AD → **Enterprise applications** → Your app
   - **Users and groups** → **Add user/group**
   - Select user → Select role (dachido_admin, customer_admin, or admin)
   - Click **"Assign"**

3. **Done!** User can now login with their email

### Changing User Roles

**Previously:** Edit `users.json`, change role field

**Now:**
1. Azure AD → **Enterprise applications** → Your app
2. **Users and groups** → Find user
3. Click **"..."** → **"Edit assignment"**
4. Change role → **Save**
5. Or: Remove from old role, add to new role

### Removing Users

**Previously:** Delete from `users.json`

**Now:**
1. Azure AD → **Enterprise applications** → Your app
2. **Users and groups** → Find user
3. Click **"..."** → **"Remove"**
4. Or: Delete user from Azure AD entirely

---

## Rollback Plan (If Issues Occur)

### Option 1: Disable Azure AD (Quick)

1. **Remove environment variables** from Azure App Service:
   - Delete `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`
2. **Restart App Service**
3. App will show error message (Azure AD not configured)

### Option 2: Restore Old Code

1. **Git checkout previous commit:**
   ```bash
   git checkout <commit-before-azure-ad>
   git push origin main
   ```
2. **Restore `users.json`** from backup
3. **Redeploy**

---

## Security Checklist

- [ ] Client secret is stored in Azure App Service Configuration (not in code)
- [ ] `JWT_SECRET_KEY` is a strong random value (32+ characters)
- [ ] HTTPS is enforced on App Service
- [ ] Token expiration is set appropriately (8 hours)
- [ ] Roles are assigned correctly in Azure AD
- [ ] Only necessary Graph API permissions are granted
- [ ] Admin consent is granted for organization
- [ ] Cookie settings use `httponly=True`, `secure=True` in production
- [ ] Redirect URI matches exactly (including `https://` and `/auth/callback`)
- [ ] App roles are created and assigned correctly
- [ ] Test users can login and access correct sections

---

## Troubleshooting

### Error: "Azure AD authentication is not configured"

**Solution:** Set environment variables in Azure App Service Configuration

### Error: "Failed to obtain access token"

**Possible causes:**
- Client secret is incorrect
- Redirect URI doesn't match
- App registration not configured correctly

**Solution:** 
- Verify `AZURE_CLIENT_SECRET` is correct
- Check redirect URI matches exactly
- Verify app registration settings

### Error: "Failed to retrieve user information"

**Possible causes:**
- API permissions not granted
- Admin consent not given

**Solution:**
- Go to App Registration → API permissions
- Click "Grant admin consent for [Your Organization]"

### User can login but has no role

**Solution:**
- Assign user to an app role in Enterprise applications
- User must be assigned to at least one role

### User can't access their organization's data

**Solution:**
- Organization is extracted from email domain
- Email format: `user@organization.com` → organization: `organization`
- If email doesn't match, organization defaults to email domain

---

## Estimated Timeline

- **Azure AD Setup:** 1-2 hours
- **Environment Variables:** 15 minutes
- **Testing:** 1 hour
- **User Migration:** 30 minutes per user

**Total: 3-4 hours** (can be done in phases)

---

## Support

If you encounter issues:
1. Check Azure Portal → App Service → Log stream for errors
2. Check browser console for JavaScript errors
3. Verify all environment variables are set correctly
4. Verify app roles are assigned in Azure AD

