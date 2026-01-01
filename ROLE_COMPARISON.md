# Role Comparison: admin vs customer_admin vs dachido_admin

## Overview

The dashboard supports three distinct user roles, each with different levels of access and permissions. This document explains the differences between them.

---

## 🔴 **dachido_admin** (Super Admin)

### Organization
- **Must belong to**: `dachido` organization only
- **Purpose**: Platform-wide super administrator

### Key Characteristics
- ✅ **Full access to ALL organizations**
- ✅ **Can view and manage data across all companies**
- ✅ **Can manage all users** (add, edit, delete users in any organization)
- ✅ **Can see User Management module** in dashboard
- ✅ **Can switch between organizations** using the organization selector dropdown
- ✅ **All permissions** (`*` wildcard - unlimited access)

### Permissions
```
dachido_admin: ['*']  # All permissions
```

### Dashboard Features
- ✅ **Organization Selector**: Dropdown to switch between organizations
- ✅ **User Management Module**: Full user CRUD operations
- ✅ **All Dashboard Modules**: HOME, MARKETING, OPERATIONS, ENGAGEMENT, ADMIN, LIBRARY
- ✅ **Cross-Organization Data**: Can view analytics for any organization
- ✅ **Audio Recordings**: Can view recordings from all organizations

### API Access
- ✅ `/api/users` - List, create, update, delete users
- ✅ `/api/audio/*` - Access audio data from all organizations
- ✅ `/api/*` - All API endpoints with organization parameter support

### Use Cases
- Platform administrators
- Support staff who need to help multiple organizations
- System administrators managing the entire platform

---

## 🟡 **admin** (Organization Admin)

### Organization
- **Belongs to**: Any organization (e.g., `coromandel`, `company1`, etc.)
- **Purpose**: Organization-level administrator

### Key Characteristics
- ✅ **Full access to their OWN organization only**
- ✅ **Can manage users in their organization** (if implemented)
- ❌ **Cannot access other organizations' data**
- ❌ **Cannot see User Management module**
- ❌ **No organization selector** (only see their own org)

### Permissions
```
admin: [
    'view_dashboard',
    'manage_users',        # Can manage users in their organization
    'view_analytics',
    'manage_recordings'   # Can manage audio recordings
]
```

### Dashboard Features
- ✅ **All Dashboard Modules**: HOME, MARKETING, OPERATIONS, ENGAGEMENT, ADMIN, LIBRARY
- ✅ **Full Admin Module**: Can see all admin features (database stats, completeness metrics)
- ✅ **Organization-Specific Data**: Only sees data for their organization
- ❌ **No User Management Module**: Not visible in navigation
- ❌ **No Organization Selector**: Only sees their own organization

### API Access
- ✅ `/api/audio/*` - Access audio data from their organization only
- ✅ `/api/home/*` - Home dashboard data for their organization
- ✅ `/api/marketing/*` - Marketing data for their organization
- ❌ `/api/users` - Cannot manage users (Dachido admin only)

### Use Cases
- Company administrators
- Organization managers
- Team leads who need full access to their organization's data

---

## 🟢 **customer_admin** (Limited Admin / Viewer)

### Organization
- **Belongs to**: Any organization (e.g., `coromandel`, `company1`, etc.)
- **Purpose**: Limited access user with view-only permissions

### Key Characteristics
- ✅ **View-only access to their OWN organization**
- ❌ **Cannot manage users**
- ❌ **Cannot modify data**
- ❌ **Limited admin features**
- ❌ **No organization selector**

### Permissions
```
customer_admin: [
    'view_dashboard',
    'view_analytics',
    'view_recordings'     # Can view but not manage
]
```

### Dashboard Features
- ✅ **Most Dashboard Modules**: HOME, MARKETING, OPERATIONS, ENGAGEMENT, LIBRARY
- ⚠️ **Limited Admin Module**: 
  - ✅ Can see: Active Users KPI, Date Coverage KPI, User Tables
  - ❌ Cannot see: Total Records KPI, Data Completeness KPI, Database Statistics
- ✅ **Organization-Specific Data**: Only sees data for their organization
- ❌ **No User Management Module**: Not visible
- ❌ **No Organization Selector**: Only sees their own organization

### API Access
- ✅ `/api/audio/*` - View audio data (read-only)
- ✅ `/api/home/*` - View home dashboard data
- ✅ `/api/marketing/*` - View marketing data
- ❌ `/api/users` - Cannot access
- ❌ `/api/admin/db-stats` - Cannot access (admin only)

### Use Cases
- End users who need to view reports
- Stakeholders who need read-only access
- Team members who don't need management capabilities

---

## 📊 Comparison Table

| Feature | dachido_admin | admin | customer_admin |
|---------|---------------|-------|----------------|
| **Organization** | `dachido` only | Any org | Any org |
| **Access Scope** | All organizations | Own organization | Own organization |
| **User Management** | ✅ All users | ❌ No | ❌ No |
| **User Management Module** | ✅ Visible | ❌ Hidden | ❌ Hidden |
| **Organization Selector** | ✅ Yes | ❌ No | ❌ No |
| **View Other Orgs** | ✅ Yes | ❌ No | ❌ No |
| **Manage Users** | ✅ Yes (all orgs) | ⚠️ Future | ❌ No |
| **Database Stats** | ✅ Yes | ✅ Yes | ❌ No |
| **Data Completeness** | ✅ Yes | ✅ Yes | ❌ No |
| **Audio Recordings** | ✅ All orgs | ✅ Own org | ✅ Own org (view) |
| **Dashboard Modules** | ✅ All | ✅ All | ✅ Most |
| **Admin Module** | ✅ Full | ✅ Full | ⚠️ Limited |
| **Permissions** | `*` (all) | 4 permissions | 3 permissions |

---

## 🔐 Permission Details

### Permission System

The system uses a permission-based access control:

```python
permissions = {
    'dachido_admin': ['*'],  # All permissions (wildcard)
    'admin': [
        'view_dashboard',
        'manage_users',
        'view_analytics',
        'manage_recordings'
    ],
    'customer_admin': [
        'view_dashboard',
        'view_analytics',
        'view_recordings'
    ]
}
```

### Organization Access

```python
def can_access_organization(user_org, target_org, user_role):
    # Dachido admins can access all organizations
    if is_dachido_admin(user_org, user_role):
        return True
    # Others can only access their own organization
    return user_org.lower() == target_org.lower()
```

---

## 🎯 Role Selection Guide

### Choose **dachido_admin** when:
- User needs to manage the entire platform
- User needs to help multiple organizations
- User is a system administrator
- User needs to create/manage users across all organizations

### Choose **admin** when:
- User is an organization manager
- User needs full access to their organization's data
- User needs to see database statistics and completeness metrics
- User may need to manage users in their organization (future feature)

### Choose **customer_admin** when:
- User only needs to view reports and analytics
- User doesn't need management capabilities
- User is an end-user or stakeholder
- User should have limited access for security reasons

---

## 🚀 Future Enhancements

Potential role improvements:
- **admin** role may get organization-level user management
- More granular permissions (e.g., `edit_recordings`, `export_data`)
- Role-based UI customization
- Custom roles with specific permission sets

---

## 📝 Examples

### Example 1: Dachido Admin
```
Organization: dachido
Username: admin
Role: dachido_admin

Can:
- See all organizations in dropdown
- View data for Coromandel, Company1, Company2, etc.
- Create users for any organization
- Access User Management module
- View all audio recordings across all organizations
```

### Example 2: Organization Admin
```
Organization: coromandel
Username: manager
Role: admin

Can:
- See only Coromandel's data
- View full admin module with database stats
- Access all dashboard modules
- View Coromandel's audio recordings
- Cannot see other organizations
- Cannot manage users
```

### Example 3: Customer Admin
```
Organization: coromandel
Username: viewer
Role: customer_admin

Can:
- See only Coromandel's data
- View most dashboard modules
- View limited admin module (no database stats)
- View Coromandel's audio recordings (read-only)
- Cannot see other organizations
- Cannot manage anything
```

---

## 🔒 Security Notes

1. **Role Validation**: Always validated on the server side
2. **Organization Isolation**: Users can only access their own organization's data (except Dachido admins)
3. **Permission Checks**: All API endpoints check permissions before allowing access
4. **JWT Tokens**: Roles are embedded in JWT tokens and verified on each request

---

## Summary

- **dachido_admin**: Platform super admin with access to everything
- **admin**: Organization admin with full access to their organization
- **customer_admin**: Limited viewer with read-only access to their organization

The main difference is **scope of access**:
- Dachido admin = All organizations
- Admin = Own organization (full access)
- Customer admin = Own organization (limited access)

