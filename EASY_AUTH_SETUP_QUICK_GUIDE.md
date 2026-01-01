# Quick Setup Guide: Azure Easy Auth

## 🚀 Step-by-Step Instructions

### Step 1: Enable Authentication in Azure Portal

1. **Go to Azure Portal**: https://portal.azure.com
2. **Find your Web App**: Search for your App Service name
3. **Open Authentication**:
   - Left sidebar → **Settings** → **Authentication**
4. **Add Identity Provider**:
   - Click **Add identity provider** button
   - Select **Microsoft** from dropdown
5. **Create App Registration**:
   - Select **Create new app registration**
   - **Name**: Enter name (e.g., "Dashboard-Auth")
   - **Supported account types**: 
     - ✅ **Accounts in any organizational directory** (recommended)
   - Click **Add**

### Step 2: Configure Authentication Behavior

1. In **Authentication** page, click **Authentication settings** (or **Edit** button)
2. Set **Action to take when request is not authenticated**:
   - ✅ **Allow anonymous requests (no action)** ← **Choose this!**
   - This allows both Easy Auth AND local auth to work
3. Click **Save**

### Step 3: Configure Redirect URI

1. **Go to Microsoft Entra ID**:
   - Search "Microsoft Entra ID" in Azure Portal
   - Click **App registrations** (left sidebar)
2. **Find Your App**:
   - Find the app registration you just created
   - Click on it
3. **Add Redirect URI**:
   - Left sidebar → **Authentication**
   - Under **Web** platform, click **+ Add URI**
   - Enter: `https://YOUR-APP-NAME.azurewebsites.net/.auth/login/aad/callback`
   - Replace `YOUR-APP-NAME` with your actual app name
   - Example: `https://my-dashboard.azurewebsites.net/.auth/login/aad/callback`
4. **Check ID Tokens**:
   - Under "Implicit grant and hybrid flows"
   - ✅ Check **ID tokens**
5. Click **Save**

### Step 4: Test It!

1. **Wait 1-2 minutes** for changes to propagate
2. **Go to your app**: `https://YOUR-APP-NAME.azurewebsites.net/login`
3. **You should be redirected** to Microsoft login page
4. **After login**, you'll be redirected back to your app

---

## 📋 Checklist

- [ ] Identity provider (Microsoft) added in App Service Authentication
- [ ] Authentication settings set to "Allow anonymous requests"
- [ ] Redirect URI added in App Registration: `/.auth/login/aad/callback`
- [ ] ID tokens checked in App Registration
- [ ] All changes saved
- [ ] Tested login flow

---

## 🔧 Common Issues

### ❌ "Redirect URI mismatch" Error

**Fix**: 
- Check redirect URI matches exactly: `https://YOUR-APP.azurewebsites.net/.auth/login/aad/callback`
- Must use `https://` (not `http://`)
- Path must be exactly `/.auth/login/aad/callback`

### ❌ Login page doesn't redirect to Microsoft

**Fix**:
- Verify Authentication is enabled and saved
- Check browser console for errors
- Clear browser cache
- Ensure web app is running (not stopped)

### ❌ User logged in but can't access dashboard

**Fix**:
- User needs to be mapped to an organization
- Go to `/admin/users` as Dachido admin
- Map the Easy Auth user to an organization/role

---

## 🎯 What Happens Next?

After Easy Auth is enabled:

1. **User visits `/login`** → Redirected to Microsoft login
2. **User logs in** → Redirected back to `/auth/easy-auth-callback`
3. **System maps user** → Checks `user_mappings.json` for organization/role
4. **JWT token generated** → Custom token with organization/role
5. **User redirected** → To dashboard with proper permissions

---

## 📞 Need Help?

- Check `AZURE_EASY_AUTH_INTEGRATION.md` for detailed documentation
- Review Azure App Service logs for errors
- Verify all steps in the checklist above

