# Azure AD Authentication Deployment Checklist

## Pre-Deployment Preparation

### 1. Backup Current System ✅

- [ ] Run `python migration_cleanup.py` to create backups
- [ ] Verify backups created in `backup_pre_azure_migration/`
- [ ] Commit current code to git: `git commit -m "Pre-Azure AD migration backup"`
- [ ] Create a git tag: `git tag pre-azure-ad-migration`
- [ ] Export current `users.json` for reference

### 2. Azure AD Setup (1-2 hours)

#### Create App Registration (see migration guide Phase 1.1)

- [ ] Go to Azure Portal → Azure Active Directory → App registrations
- [ ] Click "New registration"
- [ ] **Name**: `FieldForce Dashboard`
- [ ] **Supported account types**: ✅ **Single tenant** (Accounts in this organizational directory only)
- [ ] **Redirect URI**: 
  - Platform: **Web**
  - URI: `https://YOUR-APP.azurewebsites.net/auth/callback`
  - Replace `YOUR-APP` with your actual App Service name
- [ ] Click "Register"
- [ ] **Save Application (client) ID** → `AZURE_CLIENT_ID`
- [ ] **Save Directory (tenant) ID** → `AZURE_TENANT_ID`

#### Create Client Secret (Phase 1.2.A)

- [ ] Navigate to **Certificates & secrets**
- [ ] Click **"New client secret"**
- [ ] **Description**: `Dashboard Secret`
- [ ] **Expires**: 24 months (recommended)
- [ ] Click **"Add"**
- [ ] ⚠️ **COPY VALUE IMMEDIATELY** (you won't see it again!)
- [ ] Save securely → `AZURE_CLIENT_SECRET`

#### Configure API Permissions (Phase 1.2.B)

- [ ] Go to **"API permissions"**
- [ ] Click **"Add a permission"**
- [ ] Select **"Microsoft Graph"**
- [ ] Select **"Delegated permissions"**
- [ ] Add these permissions:
  - ✅ `User.Read` (read user profile)
  - ✅ `email` (read user email)
  - ✅ `openid` (sign in)
  - ✅ `profile` (read user profile)
- [ ] Click **"Add permissions"**
- [ ] **Click "Grant admin consent for [Your Organization]"**
- [ ] Verify consent granted (green checkmarks)

#### Create App Roles (Phase 1.2.C)

**Create dachido_admin role:**
- [ ] Go to **"App roles"**
- [ ] Click **"Create app role"**
- [ ] **Display name**: `Dachido Admin`
- [ ] **Allowed member types**: ✅ Users/Groups
- [ ] **Value**: `dachido_admin`
- [ ] **Description**: `Administrator for Dachido organization with full access`
- [ ] Click **"Apply"**

**Create customer_admin role:**
- [ ] Click **"Create app role"**
- [ ] **Display name**: `Customer Admin`
- [ ] **Allowed member types**: ✅ Users/Groups
- [ ] **Value**: `customer_admin`
- [ ] **Description**: `Administrator for customer organizations`
- [ ] Click **"Apply"**

**Create admin role:**
- [ ] Click **"Create app role"**
- [ ] **Display name**: `Admin`
- [ ] **Allowed member types**: ✅ Users/Groups
- [ ] **Value**: `admin`
- [ ] **Description**: `General administrator`
- [ ] Click **"Apply"**

### 3. User Preparation

#### Create Azure AD Users for existing users

Map from `users.json`:
- [ ] `dachido:admin` → `admin@yourdomain.com` (dachido_admin role)
- [ ] `coromandel:admin` → `admin@coromandel.com` (admin role)
- [ ] `coromandel:customer` → `customer@coromandel.com` (customer_admin role)

**For each user:**
1. Azure AD → Users → New user
2. Fill in:
   - User principal name: `user@domain.com`
   - Display name: `User Name`
   - Password: Auto-generate or set
3. Click "Create"

#### Assign Users to Roles

- [ ] Go to **Enterprise Applications** → Your App
- [ ] **Users and groups** → **Add user/group**
- [ ] For each user:
  - [ ] Select user
  - [ ] Select appropriate role
  - [ ] Click **Assign**

---

## Deployment

### 4. Environment Configuration (15 minutes)

#### Option A: Using Setup Script (Recommended)

- [ ] Run: `chmod +x setup_env.sh` (Linux/Mac) or use PowerShell script
- [ ] Run: `./setup_env.sh` (Linux/Mac) or `.\setup_env.ps1` (Windows)
- [ ] Follow prompts to enter:
  - Azure Client ID
  - Azure Client Secret
  - Azure Tenant ID
  - App Service name
  - Resource Group name
- [ ] Script will:
  - Generate JWT secret
  - Set environment variables in Azure
  - Restart app service
  - Create `.env` for local testing

#### Option B: Manual Configuration

**In Azure Portal:**
- [ ] Go to App Service → **Configuration**
- [ ] **Application settings** → **+ New application setting**

Add these settings:
- [ ] `AZURE_CLIENT_ID` = `your-client-id-here`
- [ ] `AZURE_CLIENT_SECRET` = `your-client-secret-value-here`
- [ ] `AZURE_TENANT_ID` = `your-tenant-id-here`
- [ ] `AZURE_REDIRECT_URI` = `https://your-app-name.azurewebsites.net/auth/callback`
- [ ] `JWT_SECRET_KEY` = `generate-strong-random-key` (use script: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

- [ ] Click **"Save"**
- [ ] **Restart App Service** (Configuration → Overview → Restart)

**For Local Development:**
- [ ] Create `.env` file in project root:
  ```env
  AZURE_CLIENT_ID=your-client-id
  AZURE_CLIENT_SECRET=your-client-secret
  AZURE_TENANT_ID=your-tenant-id
  AZURE_REDIRECT_URI=http://localhost:5000/auth/callback
  JWT_SECRET_KEY=your-jwt-secret-key
  ```

### 5. Code Deployment

- [ ] Verify all code changes are committed:
  ```bash
  git status
  git add .
  git commit -m "Migrate to Azure AD authentication"
  ```
- [ ] Push to main branch:
  ```bash
  git push origin main
  ```
- [ ] Wait for GitHub Actions deployment to complete
- [ ] Verify deployment succeeded in Azure Portal → Deployment Center

### 6. Post-Deployment Verification

#### Test Login Flow

- [ ] Visit: `https://your-app.azurewebsites.net/login`
- [ ] Should redirect to Microsoft login page
- [ ] Login with test user (assigned to app)
- [ ] Should redirect back to dashboard
- [ ] Check browser console for success messages
- [ ] Verify user is logged in (check for auth_token cookie)

#### Test Role-Based Access

**As Dachido Admin:**
- [ ] ✅ Should access all sections
- [ ] ✅ Should see "User Management" tab (if implemented)
- [ ] ✅ Should access all organizations' data
- [ ] ✅ Should see organization selector (if Dachido admin)

**As Customer Admin:**
- [ ] ✅ Should access dashboard
- [ ] ✅ Should see only their organization's data
- [ ] ❌ Should NOT see "User Management" tab
- [ ] ❌ Should NOT access other organizations' data

**As Admin:**
- [ ] ✅ Should access dashboard
- [ ] ✅ Should see their organization's data
- [ ] ❌ Should NOT see "User Management" tab

#### Test Token Persistence

- [ ] Login successfully
- [ ] Close browser
- [ ] Reopen app
- [ ] Should still be logged in (until token expires - 8 hours)

#### Check Logs

- [ ] Azure Portal → App Service → **Log stream**
- [ ] Look for:
  - ✅ "Azure AD authentication enabled"
  - ✅ "Azure AD login successful: organization:username (role: role)"
  - ❌ No authentication errors

---

## Rollback Plan (If Issues Occur)

### Quick Rollback

1. **Remove Azure AD environment variables:**
   - Azure Portal → App Service → Configuration
   - Delete: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`
   - Save and restart

2. **Restore from backup:**
   ```bash
   git checkout pre-azure-ad-migration
   git push origin main --force
   ```

3. **Restore users.json:**
   ```bash
   cp backup_pre_azure_migration/users.json users.json
   ```

### Full Rollback

1. **Git checkout previous commit:**
   ```bash
   git checkout <commit-before-azure-ad>
   git push origin main
   ```

2. **Restore all files from backup:**
   ```bash
   cp -r backup_pre_azure_migration/* .
   ```

---

## Post-Migration Tasks

### Cleanup (Optional)

- [ ] Archive old authentication files:
  - `auth.py` → `archive/auth.py.backup`
  - `easy_auth.py` → `archive/easy_auth.py.backup`
  - `users.json` → `archive/users.json.backup`

- [ ] Update documentation:
  - [ ] Update README.md with new login process
  - [ ] Document user management process (Azure AD)
  - [ ] Update API documentation

### User Communication

- [ ] Notify users of new login process
- [ ] Provide instructions for first-time login
- [ ] Share support contact for issues

---

## Security Verification

- [ ] Client secret stored in Azure App Service (not in code)
- [ ] `JWT_SECRET_KEY` is strong random value (32+ characters)
- [ ] HTTPS enforced on App Service
- [ ] Token expiration set to 8 hours
- [ ] Roles assigned correctly in Azure AD
- [ ] Only necessary Graph API permissions granted
- [ ] Admin consent granted for organization
- [ ] Cookie settings: `httponly=True`, `secure=True` in production
- [ ] Redirect URI matches exactly
- [ ] App roles created and assigned correctly

---

## Support & Troubleshooting

### Common Issues

**"Azure AD authentication is not configured"**
- ✅ Verify environment variables are set in Azure App Service
- ✅ Restart App Service after setting variables

**"Failed to obtain access token"**
- ✅ Check `AZURE_CLIENT_SECRET` is correct
- ✅ Verify redirect URI matches exactly
- ✅ Check app registration settings

**"Failed to retrieve user information"**
- ✅ Grant admin consent in API permissions
- ✅ Verify API permissions are correct

**"User has no role"**
- ✅ Assign user to app role in Enterprise applications
- ✅ Verify role value matches exactly (case-sensitive)

### Getting Help

1. Check Azure Portal → App Service → Log stream
2. Check browser console for errors
3. Verify all environment variables
4. Review migration guide troubleshooting section

---

## Checklist Summary

- [ ] Pre-deployment backup completed
- [ ] Azure AD App Registration created
- [ ] Client secret created and saved
- [ ] API permissions configured and consented
- [ ] App roles created (dachido_admin, customer_admin, admin)
- [ ] Users created in Azure AD
- [ ] Users assigned to roles
- [ ] Environment variables set in Azure App Service
- [ ] Code deployed
- [ ] Login flow tested
- [ ] Role-based access tested
- [ ] Token persistence tested
- [ ] Logs verified
- [ ] Security checklist completed

**Total Estimated Time: 3-4 hours**

---

## Next Steps After Deployment

1. Monitor application logs for 24-48 hours
2. Collect user feedback on login experience
3. Document any issues encountered
4. Plan for user training if needed
5. Schedule cleanup of old authentication files

