# How Organizations Get Credentials

## Current Situation

Currently, there is **NO automated process** for organizations to get credentials. Credentials are created in one of these ways:

### Method 1: Hardcoded in app.py (Current)
When the app starts, it automatically creates default users:
- Dachido admin: `dachido` / `admin` / `adminpass`
- Coromandel admin: `coromandel` / `admin` / `adminpass`
- Coromandel customer: `coromandel` / `customer` / `customer123`

### Method 2: Manual Creation by Dachido Admin
A Dachido admin can manually create users via Python script or API.

### Method 3: Self-Registration (Currently Open)
The `/register` endpoint allows anyone to create an account, but this is not secure for production.

---

## How Coromandel (or any organization) Gets Credentials

### Option A: Dachido Admin Creates Them (Recommended)

**Step 1: Dachido Admin Logs In**
- Organization: `dachido`
- Username: `admin`
- Password: `adminpass`

**Step 2: Create Organization and User**
Dachido admin runs this Python code (or uses admin interface):

```python
import auth

# Create Coromandel organization
auth.add_organization("coromandel", display_name="Coromandel")

# Create admin user for Coromandel
auth.add_user("coromandel", "admin", "secure_password_here", role="admin")

# Create additional users as needed
auth.add_user("coromandel", "manager1", "another_password", role="customer_admin")
```

**Step 3: Send Credentials to Coromandel**
Dachido admin sends credentials securely to Coromandel:
- Organization: `coromandel`
- Username: `admin`
- Password: `secure_password_here`

---

### Option B: Self-Registration (Not Recommended for Production)

**Step 1: Go to Registration Page**
- Navigate to: `http://your-app-url/register`

**Step 2: Fill Form**
- Organization: `coromandel` (or your organization name)
- Username: `admin` (or your username)
- Password: `your_password`
- Role: `admin` or `customer_admin`

**Step 3: Login**
- Use the credentials you just created

**⚠️ Security Issue**: Currently, anyone can register. This should be restricted in production.

---

### Option C: Programmatic Creation (For Bulk Setup)

Create a setup script:

```python
# setup_coromandel.py
import auth

# Create organization
auth.add_organization(
    "coromandel",
    display_name="Coromandel",
    metadata={
        "contact_email": "admin@coromandel.com",
        "created_by": "dachido_admin",
        "created_date": "2024-01-01"
    }
)

# Create users
users = [
    ("admin", "AdminPassword123!", "admin"),
    ("manager1", "ManagerPass456!", "customer_admin"),
    ("analyst1", "AnalystPass789!", "customer_admin"),
]

for username, password, role in users:
    auth.add_user("coromandel", username, password, role=role)
    print(f"Created user: {username}")

print("Coromandel organization setup complete!")
```

Run: `python setup_coromandel.py`

---

## Recommended Process for Production

### 1. Organization Onboarding Flow

**Step 1: Organization Requests Access**
- Coromandel contacts Dachido to request dashboard access
- Dachido collects: organization name, contact info, initial user details

**Step 2: Dachido Admin Creates Organization**
```python
auth.add_organization(
    "coromandel",
    display_name="Coromandel",
    metadata={
        "contact_email": "admin@coromandel.com",
        "contact_name": "John Doe",
        "subscription_tier": "premium",
        "created_date": "2024-01-01"
    }
)
```

**Step 3: Dachido Admin Creates Initial User**
```python
# Generate secure password
import secrets
initial_password = secrets.token_urlsafe(12)

auth.add_user("coromandel", "admin", initial_password, role="admin")
```

**Step 4: Send Credentials Securely**
- Email credentials to Coromandel contact
- Include: Organization name, Username, Password, Login URL
- Request password change on first login (to be implemented)

**Step 5: Coromandel Logs In**
- Organization: `coromandel`
- Username: `admin`
- Password: `[sent_password]`

**Step 6: Coromandel Creates Additional Users**
- Coromandel admin can create more users via their dashboard (to be implemented)
- Or request Dachido admin to create them

---

## What Needs to Be Built

### 1. Admin Interface for Dachido Admins
- Create/view/edit organizations
- Create/view/edit users for any organization
- Reset passwords
- View organization usage

### 2. Organization Admin Interface
- Create users within their organization
- Manage user roles (admin, customer_admin)
- Reset passwords for their users
- View user activity

### 3. Secure Registration Process
- Restrict `/register` to Dachido admins only
- Or implement invitation-based registration
- Email verification
- Password strength requirements

### 4. Password Management
- Password reset functionality
- Force password change on first login
- Password expiration policies

---

## Current Credentials for Testing

### Coromandel
- **Organization**: `coromandel`
- **Admin Username**: `admin`
- **Admin Password**: `adminpass`
- **Customer Username**: `customer`
- **Customer Password**: `customer123`

### Dachido (Super Admin)
- **Organization**: `dachido`
- **Username**: `admin`
- **Password**: `adminpass`

---

## Security Recommendations

1. **Change Default Passwords**: Immediately change default passwords in production
2. **Restrict Registration**: Disable or restrict `/register` endpoint
3. **Secure Password Storage**: Already using Bcrypt (good)
4. **Password Policies**: Implement minimum length, complexity requirements
5. **Two-Factor Authentication**: Consider adding 2FA for admin accounts
6. **Audit Logging**: Log all credential creation/changes
7. **Secure Communication**: Send credentials via encrypted email or secure portal

---

## Quick Setup Script for New Organization

Save this as `create_org.py`:

```python
#!/usr/bin/env python3
"""Create a new organization and admin user"""
import auth
import sys
import secrets

if len(sys.argv) < 3:
    print("Usage: python create_org.py <org_name> <display_name> [username]")
    print("Example: python create_org.py coromandel 'Coromandel' admin")
    sys.exit(1)

org_name = sys.argv[1].lower()
display_name = sys.argv[2]
username = sys.argv[3] if len(sys.argv) > 3 else "admin"

# Generate secure password
password = secrets.token_urlsafe(16)

# Create organization
if auth.add_organization(org_name, display_name=display_name):
    print(f"✅ Organization '{org_name}' created")
else:
    print(f"⚠️  Organization '{org_name}' already exists")

# Create admin user
if auth.add_user(org_name, username, password, role="admin"):
    print(f"✅ Admin user '{username}' created")
    print(f"\n📋 Credentials:")
    print(f"   Organization: {org_name}")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print(f"\n⚠️  Save these credentials securely!")
else:
    print(f"❌ User '{username}' already exists")
```

Run: `python create_org.py coromandel "Coromandel" admin`

---

## Summary

**For Coromandel to get credentials:**

1. **Contact Dachido Admin** - Request dashboard access
2. **Dachido Creates Account** - Creates organization and initial user
3. **Receive Credentials** - Get organization name, username, password via secure channel
4. **Login** - Use credentials to access dashboard
5. **Create More Users** - Organization admin can create additional users (once feature is built)

**Currently**: Coromandel can use the default test credentials:
- Organization: `coromandel`
- Username: `admin` 
- Password: `adminpass`

**For Production**: Implement proper onboarding process with secure credential distribution.

