# Fix: HTTP 401 Error on Easy Auth Callback

## Problem

Getting **HTTP ERROR 401** when accessing `/.auth/login/aad/callback`

This means the redirect URI is not properly configured in Microsoft Entra ID.

---

## Solution: Configure Redirect URI

### Step 1: Open App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Search for **"Microsoft Entra ID"** (or "Azure Active Directory")
3. Click **"App registrations"** in the left sidebar
4. Find your app: **"fieldforce-dashboard"**
   - Or search by Client ID: `6da24c1c-781a-45e3-b5f4-b539380616ab`

### Step 2: Add Redirect URI

1. Click on your app registration
2. In the left sidebar, click **"Authentication"**
3. Under **"Platform configurations"**, find **"Web"** platform
   - If "Web" doesn't exist, click **"+ Add a platform"** and select **"Web"**
4. In **"Redirect URIs"**, click **"+ Add URI"**
5. Add this **exact** URI:
   ```
   https://fieldforce-dashboard.azurewebsites.net/.auth/login/aad/callback
   ```
   **Important**: 
   - Must use `https://` (not `http://`)
   - Must match your app URL exactly
   - Path must be exactly `/.auth/login/aad/callback`

6. Under **"Implicit grant and hybrid flows"**, check:
   - ✅ **ID tokens**

7. Click **"Save"** at the top

### Step 3: Verify Configuration

After saving, verify:
- ✅ Redirect URI appears in the list
- ✅ ID tokens is checked
- ✅ Platform is "Web"

---

## Common Issues

### Issue 1: Redirect URI Mismatch

**Error**: "AADSTS50011: The redirect URI specified in the request does not match..."

**Fix**:
- Check the redirect URI matches **exactly** (case-sensitive)
- Must include `https://`
- Must include full domain: `fieldforce-dashboard.azurewebsites.net`
- Path must be: `/.auth/login/aad/callback`

### Issue 2: Wrong Platform Type

**Error**: Redirect URI not accepted

**Fix**:
- Make sure you're adding to **"Web"** platform, not "Single-page application" or "Mobile"
- If "Web" doesn't exist, add it first

### Issue 3: ID Tokens Not Checked

**Error**: Authentication works but no user info

**Fix**:
- Check **"ID tokens"** under "Implicit grant and hybrid flows"
- This is required for Easy Auth to work

---

## Testing After Fix

1. **Wait 1-2 minutes** for changes to propagate
2. **Clear browser cache** (Ctrl+Shift+Delete)
3. **Go to**: `https://fieldforce-dashboard.azurewebsites.net/login`
4. **Should redirect** to Microsoft login
5. **After login**, should redirect to callback successfully
6. **Should see dashboard** (or mapping page if user not mapped)

---

## Verification Checklist

- [ ] Redirect URI added in App Registration
- [ ] URI matches exactly: `https://fieldforce-dashboard.azurewebsites.net/.auth/login/aad/callback`
- [ ] Platform is "Web"
- [ ] ID tokens is checked
- [ ] Changes saved
- [ ] Waited 1-2 minutes
- [ ] Cleared browser cache
- [ ] Tested login flow

---

## Alternative: Check Current Redirect URIs

To see what's currently configured:

1. Go to App Registration → Authentication
2. Look at "Redirect URIs" section
3. Verify your callback URL is listed
4. If not, add it following steps above

---

## Still Getting 401?

If you still get 401 after configuring redirect URI:

1. **Check App Registration Client ID** matches the one in Azure Portal
2. **Verify App Service Authentication** is enabled
3. **Check Azure App Service logs** for detailed errors
4. **Try incognito/private window** to rule out cache issues
5. **Verify the app registration** is linked to your App Service

---

## Quick Reference

**Redirect URI Format:**
```
https://YOUR-APP-NAME.azurewebsites.net/.auth/login/aad/callback
```

**For your app:**
```
https://fieldforce-dashboard.azurewebsites.net/.auth/login/aad/callback
```

**Where to configure:**
- Azure Portal → Microsoft Entra ID → App registrations → Your App → Authentication → Web platform → Redirect URIs

