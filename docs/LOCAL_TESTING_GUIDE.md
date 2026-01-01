# Local Testing Guide

## ✅ What Works Locally

### 1. **Local Authentication** (Username/Password)
- ✅ Full user management (create, edit, delete users)
- ✅ JWT token generation and validation
- ✅ RBAC roles (dachido_admin, admin, customer_admin)
- ✅ Organization-based access control
- ✅ All dashboard modules
- ✅ User Management module (Dachido admin)

### 2. **What Doesn't Work Locally**
- ❌ Easy Auth (requires Azure App Service)
- ❌ Automatic email mapping (requires Easy Auth)
- ❌ Microsoft login redirect

---

## 🧪 How to Test Locally

### Step 1: Start Your Flask App

```bash
# Navigate to project directory
cd C:\Users\satya\Downloads\dashboard

# Run Flask app
python app.py
# or
flask run
```

App should start at: `http://127.0.0.1:5000`

### Step 2: Test Local Authentication

1. **Go to**: `http://127.0.0.1:5000/login`
2. **You'll see**: Local login form (not Microsoft redirect)
3. **Log in with**:
   ```
   Organization: dachido
   Username: admin
   Password: (your Dachido admin password)
   ```

### Step 3: Test User Management

1. **Log in as Dachido admin**
2. **Click "USER MANAGEMENT" tab**
3. **Test features**:
   - ✅ View all users
   - ✅ Add new user
   - ✅ Edit user (role, password, email)
   - ✅ Delete user

### Step 4: Create Test Users

**Add a user with email** (for future Easy Auth mapping):

```
Organization: coromandel
Username: test.user
Password: TestPass123!
Role: admin
Email: test.user@coromandel.com
```

**Why add email?**
- Even though Easy Auth won't work locally
- The email will be saved in `users.json`
- When you deploy to Azure and enable Easy Auth, the email will be there for automatic mapping

### Step 5: Test Different Roles

**Test as different users:**

1. **Dachido Admin**:
   ```
   Organization: dachido
   Username: admin
   ```
   - Should see: User Management module
   - Should see: Organization selector
   - Should see: All organizations' data

2. **Organization Admin**:
   ```
   Organization: coromandel
   Username: admin
   ```
   - Should see: All dashboard modules
   - Should NOT see: User Management module
   - Should see: Only Coromandel's data

3. **Customer Admin**:
   ```
   Organization: coromandel
   Username: customer
   ```
   - Should see: Most dashboard modules
   - Should see: Limited Admin module
   - Should NOT see: Database statistics

---

## 🔍 How the Code Handles Local vs Azure

### Authentication Flow

```python
# auth.py - get_user_from_token()

1. Try Easy Auth first
   ↓ (checks for X-MS-CLIENT-PRINCIPAL-ID header)
   ↓ (won't exist locally, so skips)
   
2. Fall back to JWT token
   ↓ (checks auth_token cookie)
   ↓ (works locally!)
   
3. Return user info
```

### Login Flow

```python
# app.py - login()

1. Check if Easy Auth enabled
   ↓ (is_easy_auth_enabled() checks headers)
   ↓ (returns False locally)
   
2. Show local login form
   ↓ (username/password)
   
3. Generate JWT token
   ↓ (works locally!)
   
4. Set cookie and redirect
```

---

## 📝 Testing Checklist

### User Management
- [ ] Create user with email
- [ ] Create user without email
- [ ] Edit user role
- [ ] Edit user password
- [ ] Edit user email
- [ ] Delete user
- [ ] View all users

### Authentication
- [ ] Login as Dachido admin
- [ ] Login as Organization admin
- [ ] Login as Customer admin
- [ ] Logout
- [ ] JWT token expires after 30 minutes

### RBAC
- [ ] Dachido admin sees User Management
- [ ] Organization admin doesn't see User Management
- [ ] Customer admin sees limited Admin module
- [ ] Organization data isolation works

### Dashboard Modules
- [ ] All modules load correctly
- [ ] Data filters by organization
- [ ] Organization selector works (Dachido admin only)

---

## 🚀 Testing Easy Auth Flow (Azure Only)

To test the **full Easy Auth integration**, you need to:

1. **Deploy to Azure**
2. **Enable Easy Auth** in Azure Portal
3. **Configure redirect URI**
4. **Test login** via Microsoft account
5. **Verify automatic mapping** (if email matches)

**Local testing covers:**
- ✅ User management functionality
- ✅ RBAC system
- ✅ JWT token system
- ✅ Organization isolation
- ✅ All dashboard features

**Azure testing covers:**
- ✅ Easy Auth integration
- ✅ Automatic email mapping
- ✅ Microsoft login flow
- ✅ Production environment

---

## 💡 Tips for Local Testing

### 1. Create Test Users

```bash
# Via Dashboard (Recommended)
1. Log in as Dachido admin
2. Go to User Management
3. Add test users with different roles

# Or manually edit users.json
{
  "coromandel:test1": {
    "password": "$2b$12$...",
    "role": "admin",
    "organization": "coromandel",
    "username": "test1",
    "email": "test1@coromandel.com"
  }
}
```

### 2. Test Email Matching

Even though Easy Auth won't work locally, you can:
- ✅ Add emails to users in `users.json`
- ✅ Verify emails are saved correctly
- ✅ Test that email field appears in User Management
- ✅ When deployed to Azure, automatic mapping will work if emails match

### 3. Check Console Logs

The code has debug logging:
```python
# Look for these in console:
✅ Login successful: coromandel:admin (role: admin)
✅ JWT token generated: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
✅ Token verified successfully for: coromandel:admin
```

### 4. Test Edge Cases

- ✅ Login with wrong password
- ✅ Login with wrong organization
- ✅ Access protected route without login
- ✅ Access route with expired token
- ✅ Try to delete your own account (should fail)

---

## 🐛 Common Local Testing Issues

### Issue: "No auth_token cookie found"

**Cause**: Not logged in or cookie expired

**Fix**: Log in again at `/login`

### Issue: "Module element not found: users-module"

**Cause**: Not logged in as Dachido admin

**Fix**: Log in with Dachido admin credentials

### Issue: User Management not visible

**Cause**: Not a Dachido admin

**Fix**: Log in as `dachido:admin`

### Issue: Can't create user

**Cause**: Missing required fields or user already exists

**Fix**: Check all fields are filled, use unique username

---

## 📊 Summary

**Local Testing:**
- ✅ **Works**: User management, authentication, RBAC, all features
- ❌ **Doesn't work**: Easy Auth (Azure-specific)

**What to Test Locally:**
1. User Management (create, edit, delete)
2. Different user roles
3. RBAC permissions
4. Organization isolation
5. Dashboard functionality

**What to Test in Azure:**
1. Easy Auth login flow
2. Automatic email mapping
3. Microsoft account integration
4. Production environment

---

## ✅ Ready to Test?

1. **Start Flask app**: `python app.py`
2. **Go to**: `http://127.0.0.1:5000/login`
3. **Log in**: `dachido:admin`
4. **Test User Management**: Click "USER MANAGEMENT" tab
5. **Create test users**: Add users with emails
6. **Test different roles**: Log in as different users

Everything except Easy Auth works perfectly locally! 🎉

