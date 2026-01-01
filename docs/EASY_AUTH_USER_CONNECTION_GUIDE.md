# Connecting Local User Management with Azure Easy Auth

## Overview

This guide explains how to connect users created in your local user management system (with username/password and RBAC roles) to Azure Easy Auth (Microsoft Entra ID authentication).

---

## 🔄 Two Authentication Systems

Your application supports **two authentication methods**:

### 1. **Local Authentication** (users.json)
- Users stored in `users.json`
- Username/password authentication
- Organization, role, and password managed locally
- Used for: Development, fallback, or when Easy Auth is disabled

### 2. **Azure Easy Auth** (Microsoft Entra ID)
- Authentication handled by Azure/Microsoft
- Users authenticate via Microsoft login
- No password management needed
- Used for: Production, enterprise SSO

### The Connection: **user_mappings.json**

The bridge between these two systems is `user_mappings.json`, which maps:
- **Easy Auth Identity** (Microsoft account) → **Local User Account** (organization, username, role)

---

## 🔗 How the Connection Works

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│  User logs in via Azure Easy Auth (Microsoft Login)         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Azure Easy Auth authenticates user                        │
│  Returns: Easy Auth User ID + Email                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  System checks user_mappings.json                           │
│  Looks for: easy_auth_id or email                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
    Found?                      Not Found?
         │                           │
         ▼                           ▼
┌──────────────────┐    ┌──────────────────────────────┐
│ Use mapping to   │    │ Check users.json for         │
│ get organization │    │ matching email               │
│ and role         │    └──────────┬───────────────────┘
└────────┬─────────┘               │
         │                    ┌────┴────┐
         │                    │         │
         │              Found?    Not Found?
         │                    │         │
         │                    ▼         ▼
         │            ┌──────────┐  ┌──────────────┐
         │            │ Auto-map │  │ Manual map   │
         │            │ to org   │  │ required     │
         │            └────┬─────┘  └──────────────┘
         │                 │
         └─────────────────┴──────────────┐
                                          │
                                          ▼
                           ┌──────────────────────────────┐
                           │ Generate Custom JWT Token    │
                           │ with organization & role      │
                           └──────────────────────────────┘
```

---

## 📝 Step-by-Step: Connecting Users

### Scenario: You create a user locally, then they need to use Easy Auth

#### Step 1: Create User Locally (via User Management)

1. **Log in as Dachido Admin**
2. **Go to User Management module**
3. **Click "+ Add User"**
4. **Fill in the form**:
   ```
   Organization: coromandel
   Username: john.doe
   Password: SecurePassword123!
   Role: admin
   Email: john.doe@coromandel.com  ← IMPORTANT!
   ```
5. **Click "Create User"**

**Result**: User is created in `users.json`:
```json
{
  "coromandel:john.doe": {
    "password": "$2b$12$...",
    "role": "admin",
    "organization": "coromandel",
    "username": "john.doe",
    "email": "john.doe@coromandel.com",
    "created_at": "2025-12-28T10:00:00"
  }
}
```

#### Step 2: User Logs in via Easy Auth

1. **User visits** `https://your-app.azurewebsites.net/login`
2. **Redirected to Microsoft login**
3. **User authenticates** with their Microsoft account
4. **Microsoft returns**: 
   - Easy Auth User ID: `abc123-def456-ghi789`
   - Email: `john.doe@coromandel.com`

#### Step 3: Automatic Mapping (if email matches)

The system automatically:
1. Checks `user_mappings.json` for existing mapping
2. If not found, checks `users.json` for matching email
3. Finds `john.doe@coromandel.com` in `users.json`
4. **Automatically creates mapping** in `user_mappings.json`:
```json
{
  "easy_auth_id:abc123-def456-ghi789": {
    "organization": "coromandel",
    "role": "admin",
    "username": "john.doe",
    "easy_auth_id": "abc123-def456-ghi789",
    "email": "john.doe@coromandel.com"
  },
  "email:john.doe@coromandel.com": {
    "organization": "coromandel",
    "role": "admin",
    "username": "john.doe",
    "easy_auth_id": "abc123-def456-ghi789",
    "email": "john.doe@coromandel.com"
  }
}
```
5. **Generates JWT token** with organization and role
6. **User is logged in** with their assigned role

---

## 🎯 Two Connection Methods

### Method 1: Automatic Mapping (Recommended)

**How it works:**
- User is created in `users.json` with an **email address**
- When user logs in via Easy Auth, system matches email automatically
- Mapping is created automatically

**Requirements:**
- ✅ User must have `email` field in `users.json`
- ✅ Easy Auth email must match `users.json` email exactly
- ✅ Case-insensitive matching

**Example:**
```json
// users.json
{
  "coromandel:john.doe": {
    "email": "john.doe@coromandel.com",  // Must match Easy Auth email
    "role": "admin",
    ...
  }
}
```

### Method 2: Manual Mapping (Dachido Admin)

**When to use:**
- Email doesn't match
- User doesn't have email in `users.json`
- You want to manually control the mapping

**Steps:**
1. **User logs in via Easy Auth** (gets redirected to mapping page if not mapped)
2. **Dachido admin goes to** `/admin/users` or `/auth/map-user`
3. **Enter mapping details**:
   - Easy Auth User ID (from Azure headers)
   - Organization
   - Username
   - Role
4. **Save mapping**

**Result**: Mapping is saved in `user_mappings.json`

---

## 🔧 Implementation Details

### File Structure

```
users.json              → Local user accounts
├── coromandel:john.doe
│   ├── password (hashed)
│   ├── role: "admin"
│   ├── organization: "coromandel"
│   ├── username: "john.doe"
│   └── email: "john.doe@coromandel.com"  ← Used for auto-mapping

user_mappings.json      → Easy Auth → Local User mapping
├── easy_auth_id:abc123
│   ├── organization: "coromandel"
│   ├── role: "admin"
│   ├── username: "john.doe"
│   ├── easy_auth_id: "abc123"
│   └── email: "john.doe@coromandel.com"
└── email:john.doe@coromandel.com
    └── (same mapping data)
```

### Code Flow

1. **User logs in via Easy Auth**
   ```python
   # easy_auth.py - get_user_from_easy_auth()
   easy_auth_user_id, email = get_easy_auth_user()
   organization, role, username = map_easy_auth_to_organization(easy_auth_user_id, email)
   ```

2. **Mapping lookup**
   ```python
   # easy_auth.py - map_easy_auth_to_organization()
   # 1. Check user_mappings.json for existing mapping
   # 2. If not found, check users.json for matching email
   # 3. Auto-create mapping if email matches
   # 4. Return organization, role, username
   ```

3. **JWT token generation**
   ```python
   # auth.py - generate_jwt_token()
   token = generate_jwt_token(username, organization, role)
   # Token includes: username, organization, role
   ```

---

## ✅ Best Practices

### 1. Always Add Email When Creating Users

**Good:**
```json
{
  "coromandel:john.doe": {
    "email": "john.doe@coromandel.com",  // ✅ Enables auto-mapping
    "role": "admin",
    ...
  }
}
```

**Bad:**
```json
{
  "coromandel:john.doe": {
    // ❌ No email - requires manual mapping
    "role": "admin",
    ...
  }
}
```

### 2. Use Consistent Email Addresses

- Use the same email in `users.json` as the user's Microsoft account
- Easy Auth will return the Microsoft account email
- Matching emails = automatic mapping

### 3. Verify Email Before Creating User

Before creating a user:
1. Ask: "What's your Microsoft/Office 365 email?"
2. Use that exact email in `users.json`
3. User will be auto-mapped on first Easy Auth login

### 4. Keep Passwords for Fallback

Even with Easy Auth enabled:
- Keep passwords in `users.json` for:
  - Local development
  - Fallback if Easy Auth is disabled
  - Emergency access

---

## 🔄 Workflow Examples

### Example 1: New User Setup (Automatic)

```
1. Dachido admin creates user:
   - Organization: coromandel
   - Username: jane.smith
   - Email: jane.smith@coromandel.com
   - Role: customer_admin

2. User logs in via Easy Auth:
   - Uses Microsoft account: jane.smith@coromandel.com
   - System finds matching email in users.json
   - Auto-creates mapping
   - User logged in as coromandel:customer_admin

✅ No manual intervention needed!
```

### Example 2: New User Setup (Manual)

```
1. Dachido admin creates user:
   - Organization: coromandel
   - Username: bob.jones
   - Email: (not provided or different)

2. User logs in via Easy Auth:
   - Uses Microsoft account: bob.jones@microsoft.com
   - System can't find matching email
   - User redirected to mapping page

3. Dachido admin maps user:
   - Easy Auth ID: xyz789
   - Organization: coromandel
   - Username: bob.jones
   - Role: admin

4. User logs in again:
   - Mapping found
   - User logged in as coromandel:admin

⚠️ Requires manual mapping
```

### Example 3: Existing User Enables Easy Auth

```
1. User already exists in users.json:
   - coromandel:john.doe
   - Email: john.doe@coromandel.com
   - Role: admin

2. Easy Auth is enabled on Azure

3. User logs in via Easy Auth:
   - Microsoft account: john.doe@coromandel.com
   - System finds matching email
   - Auto-creates mapping
   - User continues with same role

✅ Seamless transition!
```

---

## 🛠️ Troubleshooting

### Issue: User can't log in after Easy Auth

**Symptoms:**
- User authenticates with Microsoft
- Gets "User not mapped" error
- Redirected to mapping page

**Solutions:**
1. **Check email match**:
   - Verify email in `users.json` matches Microsoft email
   - Check for typos or case differences

2. **Manual mapping**:
   - Go to `/admin/users` as Dachido admin
   - Manually create mapping

3. **Check user_mappings.json**:
   - Verify mapping exists
   - Check for correct organization/role

### Issue: User has wrong role after Easy Auth login

**Cause**: Mapping has incorrect role

**Solution**:
1. Update role in `users.json`
2. Delete mapping in `user_mappings.json`
3. User logs in again (auto-mapping recreates with correct role)

Or:
1. Update mapping directly in `user_mappings.json`
2. User logs in again

### Issue: User exists but auto-mapping doesn't work

**Possible causes**:
- Email doesn't match exactly
- Email not in `users.json`
- `user_mappings.json` permissions issue

**Solution**:
1. Check email in `users.json` matches Easy Auth email
2. Add/update email in `users.json`
3. Delete existing mapping (if wrong)
4. User logs in again

---

## 📋 Quick Reference

### Creating Users for Easy Auth

```bash
# Via Dashboard (Recommended)
1. Go to User Management
2. Add user with email matching Microsoft account
3. User logs in via Easy Auth → Auto-mapped ✅

# Via API
POST /api/users
{
  "organization": "coromandel",
  "username": "john.doe",
  "password": "temp123",  // Still needed for fallback
  "role": "admin",
  "email": "john.doe@coromandel.com"  // Must match Microsoft email
}
```

### Manual Mapping

```bash
# Via Dashboard
1. Go to /admin/users
2. Click "Map Easy Auth User"
3. Enter Easy Auth ID, organization, username, role

# Via API (if implemented)
POST /auth/map-user
{
  "easy_auth_id": "abc123",
  "organization": "coromandel",
  "username": "john.doe",
  "role": "admin"
}
```

---

## 🎯 Summary

**The Connection Process:**

1. **Create user locally** → `users.json` (with email!)
2. **User logs in via Easy Auth** → Microsoft authenticates
3. **System maps** → `user_mappings.json` (automatic if email matches)
4. **JWT token generated** → With organization and role from local user
5. **User accesses dashboard** → With correct RBAC permissions

**Key Points:**
- ✅ Email is the bridge between systems
- ✅ Automatic mapping if emails match
- ✅ Manual mapping available if needed
- ✅ Local passwords still useful for fallback
- ✅ RBAC roles come from local user management

**Best Practice:**
Always add email when creating users, matching their Microsoft account email. This enables automatic mapping and seamless Easy Auth integration.

