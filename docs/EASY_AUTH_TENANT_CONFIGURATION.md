# Easy Auth Tenant Configuration Fix

## Error: AADSTS50020

**Error Message:**
```
User account 'sanjeev@dachido.com' from identity provider 'live.com' 
does not exist in tenant 'Default Directory' and cannot access the application
```

## Problem

Your app registration is configured for **"Accounts in this organizational directory only"** (single-tenant), but the user is trying to log in with:
- A personal Microsoft account (`live.com`)
- Or an account from a different tenant

---

## Solution 1: Allow External Accounts (Recommended)

Change your app registration to allow accounts from any organization:

### Steps:

1. **Go to Azure Portal** → **Microsoft Entra ID** → **App registrations**
2. **Find your app**: "fieldforce-dashboard"
3. **Click on it** to open
4. **Click "Authentication"** in the left sidebar
5. **Under "Supported account types"**, click **"Edit"**
6. **Select one of these options**:

   **Option A: Multi-tenant (Recommended for SaaS)**
   - ✅ **"Accounts in any organizational directory"**
   - Allows users from any Azure AD tenant
   - Best for multi-organization access

   **Option B: Multi-tenant + Personal Accounts**
   - ✅ **"Accounts in any organizational directory and personal Microsoft accounts"**
   - Allows both organizational and personal Microsoft accounts
   - Most flexible option

7. **Click "Save"**

### After Changing:

- Users from any organization can log in
- Personal Microsoft accounts can log in (if Option B selected)
- No need to add users as guests

---

## Solution 2: Add User as Guest (If Keeping Single-Tenant)

If you want to keep single-tenant but allow specific external users:

### Steps:

1. **Go to Azure Portal** → **Microsoft Entra ID** → **Users**
2. **Click "+ New guest user"**
3. **Enter user's email**: `sanjeev@dachido.com`
4. **Click "Invite"**
5. **User receives invitation email**
6. **User accepts invitation**
7. **User can now log in**

**Note**: This must be done for each external user.

---

## Solution 3: Use Account in Your Tenant

If you want to test with an account that's already in your tenant:

1. **Use an account** that exists in your Azure AD tenant
2. **Or create a test user** in your tenant:
   - Azure Portal → Microsoft Entra ID → Users → New user
   - Create user with email in your tenant domain

---

## Recommended Configuration for Your Use Case

Since you have multiple organizations (Coromandel, Dachido, etc.), I recommend:

**"Accounts in any organizational directory"**

**Why?**
- ✅ Supports multiple organizations
- ✅ Users from different Azure AD tenants can log in
- ✅ No need to add each user as a guest
- ✅ Works with custom domains (like @coromandel.com, @dachido.com)
- ✅ Better for SaaS/multi-tenant scenarios

---

## How to Change Account Types

1. **App Registration** → **Authentication**
2. **Click "Edit"** next to "Supported account types"
3. **Select**: "Accounts in any organizational directory"
4. **Click "Save"**
5. **Wait 1-2 minutes** for changes to propagate

---

## After Changing

1. **Test login again** with `sanjeev@dachido.com`
2. **Should work** if the account exists in an Azure AD tenant
3. **If still fails**, the account might not exist in any Azure AD tenant (personal Microsoft account only)

---

## Personal Microsoft Accounts vs Organizational Accounts

- **Personal Microsoft Account** (`@outlook.com`, `@hotmail.com`, `@live.com`):
  - Not in any Azure AD tenant
  - Requires "Accounts in any organizational directory and personal Microsoft accounts" option

- **Organizational Account** (`@dachido.com`, `@coromandel.com`):
  - Exists in an Azure AD tenant
  - Works with "Accounts in any organizational directory"

---

## Quick Decision Guide

**Choose "Accounts in any organizational directory" if:**
- ✅ You have multiple organizations
- ✅ Users have organizational emails (@dachido.com, @coromandel.com)
- ✅ You want users from different companies to access

**Choose "Accounts in any organizational directory and personal Microsoft accounts" if:**
- ✅ You also want to allow personal Microsoft accounts
- ✅ Users might use @outlook.com, @hotmail.com emails
- ✅ Maximum flexibility needed

**Keep "Accounts in this organizational directory only" if:**
- ✅ Only your organization's users should access
- ✅ You're okay adding external users as guests manually

---

## Next Steps

1. **Change account type** to "Accounts in any organizational directory"
2. **Save changes**
3. **Wait 1-2 minutes**
4. **Test login** again
5. **Should work** if the user's email is in an Azure AD tenant

