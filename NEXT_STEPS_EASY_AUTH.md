# Next Steps: After Easy Auth is Configured

## ✅ Current Status

Based on your Azure Portal screenshot:
- ✅ Easy Auth is **Enabled**
- ✅ Microsoft identity provider is **configured**
- ✅ App (client) ID: `6da24c1c-781a-45e3-b5f4-b539380616ab`
- ⚠️ **Action needed**: Configure redirect URI

---

## 🔧 Step 1: Configure Redirect URI in Microsoft Entra ID

### 1.1 Open App Registration

1. In Azure Portal, search for **"Microsoft Entra ID"** (or "Azure Active Directory")
2. Click **"App registrations"** in the left sidebar
3. Find your app: **"fieldforce-dashboard"** (or search by Client ID: `6da24c1c-781a-45e3-b5f4-b539380616ab`)
4. Click on it to open

### 1.2 Add Redirect URI

1. In the left sidebar, click **"Authentication"**
2. Under **"Platform configurations"**, find **"Web"** platform (or click **"+ Add a platform"** and select **"Web"**)
3. In **"Redirect URIs"**, click **"+ Add URI"**
4. Add this exact URI:
   ```
   https://fieldforce-dashboard.azurewebsites.net/.auth/login/aad/callback
   ```
   *(Replace `fieldforce-dashboard` with your actual app name if different)*

5. Under **"Implicit grant and hybrid flows"**, check:
   - ✅ **ID tokens**

6. Click **"Save"**

---

## 🧪 Step 2: Test Easy Auth Login

1. **Wait 1-2 minutes** for changes to propagate
2. **Go to your app**: `https://fieldforce-dashboard.azurewebsites.net/login`
3. **You should be redirected** to Microsoft login page
4. **Log in** with a Microsoft account
5. **After login**, you'll be redirected back to your app

**Expected behavior:**
- If user is mapped → Logged in with correct role
- If user is NOT mapped → Redirected to mapping page (or error)

---

## 👥 Step 3: Create Test Users

### Option A: Create User via Dashboard (Recommended)

1. **Log in as Dachido admin** (using local auth if Easy Auth not working yet)
2. **Go to User Management module**
3. **Click "+ Add User"**
4. **Fill in form**:
   ```
   Organization: coromandel
   Username: test.user
   Password: TestPass123!
   Role: admin
   Email: test.user@coromandel.com  ← Must match Microsoft account email!
   ```
5. **Click "Create User"**

### Option B: Create User via API

```bash
POST /api/users
{
  "organization": "coromandel",
  "username": "test.user",
  "password": "TestPass123!",
  "role": "admin",
  "email": "test.user@coromandel.com"
}
```

---

## 🔗 Step 4: Test User Mapping

### Test Automatic Mapping

1. **Create a user** with email matching a Microsoft account
2. **Log out** (if logged in)
3. **Go to** `/login`
4. **Log in via Easy Auth** with the Microsoft account that matches the email
5. **Check if automatic mapping works**:
   - ✅ Should log in successfully
   - ✅ Should have correct organization and role
   - ✅ Should see dashboard with correct permissions

### If Mapping Fails

1. **Check browser console** for errors
2. **Check** `user_mappings.json` file (should be auto-created)
3. **Verify email matches** exactly (case-insensitive)
4. **Manual mapping** (if needed):
   - Log in as Dachido admin
   - Go to `/admin/users`
   - Map the Easy Auth user manually

---

## ⚙️ Step 5: Adjust Authentication Settings (Optional)

Currently your settings show:
- **Restrict access**: Require authentication
- **Unauthenticated requests**: Return HTTP 401 Unauthorized

**Recommendation**: Change to allow both Easy Auth and local auth:

1. In Azure Portal, go to **Authentication** settings
2. Click **"Edit"** next to "Authentication settings"
3. Change **"Action to take when request is not authenticated"** to:
   - ✅ **"Allow anonymous requests (no action)"**
4. Click **"Save"**

**Why?**
- Allows both Easy Auth and local authentication
- Better for development and testing
- Users can still use username/password if needed

---

## 📋 Step 6: Verify Everything Works

### Checklist

- [ ] Redirect URI added in App Registration
- [ ] Easy Auth login redirects to Microsoft
- [ ] User can log in via Easy Auth
- [ ] User is mapped to correct organization/role
- [ ] User sees correct dashboard
- [ ] User Management module works (Dachido admin)
- [ ] Automatic mapping works (email matching)
- [ ] JWT token includes organization and role

---

## 🐛 Troubleshooting

### Issue: "Redirect URI mismatch" Error

**Fix:**
- Verify redirect URI in App Registration matches exactly
- Must be: `https://YOUR-APP-NAME.azurewebsites.net/.auth/login/aad/callback`
- Check for typos or wrong domain

### Issue: User Not Mapped After Login

**Fix:**
1. Check email in `users.json` matches Microsoft account email
2. Check `user_mappings.json` exists and has correct mapping
3. Try manual mapping via `/admin/users`

### Issue: Can't Access Dashboard After Easy Auth Login

**Fix:**
1. Check user has correct role in `users.json`
2. Verify mapping in `user_mappings.json`
3. Check browser console for errors
4. Verify JWT token includes organization and role

---

## 🎯 Summary

**Immediate Next Steps:**
1. ✅ Add redirect URI in Microsoft Entra ID App Registration
2. ✅ Test Easy Auth login
3. ✅ Create test user with email
4. ✅ Test automatic mapping
5. ✅ Adjust authentication settings (optional)

**After Setup:**
- Users can log in via Microsoft account
- Automatic mapping if email matches
- Manual mapping available if needed
- RBAC roles from local user management

---

## 📞 Need Help?

- Check `EASY_AUTH_SETUP_QUICK_GUIDE.md` for detailed setup
- Check `EASY_AUTH_USER_CONNECTION_GUIDE.md` for user mapping details
- Review Azure App Service logs for errors
- Check browser console for frontend errors

