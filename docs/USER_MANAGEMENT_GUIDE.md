# User Management Feature Guide

## Overview

The User Management feature is integrated directly into the Dachido Dashboard, allowing Dachido admins to add, edit, and delete users from within the dashboard interface.

## Location

- **Module**: "USER MANAGEMENT" tab in the navigation menu
- **Visibility**: Only visible to Dachido admins
- **Position**: Appears after the "LIBRARY" module in the navigation

## How It Works

### 1. Accessing User Management

1. **Log in as Dachido Admin**:
   - Organization: `dachido`
   - Username: `admin`
   - Password: (your Dachido admin password)

2. **Navigate to User Management**:
   - Click on the **"USER MANAGEMENT"** tab in the top navigation
   - The module will load and display all users across all organizations

### 2. Viewing Users

The User Management module displays a table with:
- **Organization**: The organization the user belongs to (with display name if available)
- **Username**: The user's login username
- **Role**: User's role badge (color-coded):
  - 🔴 **Dachido Admin** (red badge)
  - 🟡 **Admin** (yellow badge)
  - 🟢 **Customer Admin** (green badge)
- **Created**: Date when the user was created
- **Actions**: Edit and Delete buttons

### 3. Adding a New User

1. Click the **"+ Add User"** button at the top
2. Fill in the form:
   - **Organization** *: Organization name (e.g., `coromandel`)
   - **Username** *: Login username
   - **Password** *: User's password
   - **Role** *: Select from dropdown:
     - Customer Admin
     - Admin
     - Dachido Admin
   - **Email** (Optional): User's email address
3. Click **"Create User"**
4. Success message will appear, and the user will be added to the table

**Note**: If the organization doesn't exist, it will be automatically created.

### 4. Editing a User

1. Click the **"Edit"** button next to the user you want to edit
2. A prompt will ask for:
   - **New Role**: Enter the new role (admin, customer_admin, or dachido_admin)
   - **New Password**: Enter new password (leave blank to keep current)
   - **Email**: Enter email (leave blank to keep current)
3. Click OK to save changes
4. Success message will appear, and the table will refresh

### 5. Deleting a User

1. Click the **"Delete"** button next to the user you want to delete
2. Confirm the deletion in the popup
3. The user will be removed from the system
4. Success message will appear, and the table will refresh

**Note**: You cannot delete your own account (the current logged-in user).

## Features

### Real-Time Updates
- All changes (add/edit/delete) are immediately reflected in the table
- No page refresh needed
- Success/error messages appear at the top of the module

### Organization Auto-Creation
- If you add a user to a non-existent organization, the organization is automatically created
- Organization display names can be set later via the organizations.json file

### Role Management
- **Dachido Admin**: Full access to all organizations and features
- **Admin**: Organization-level admin with management capabilities
- **Customer Admin**: Limited access, view-only for most features

### Security
- Only Dachido admins can access this module
- All API calls require authentication
- Passwords are hashed using bcrypt before storage
- Cannot delete your own account (prevents lockout)

## API Endpoints (Backend)

The User Management module uses these API endpoints:

### List Users
```
GET /api/users
```
Returns: List of all users with organization, username, role, and creation date

### Create User
```
POST /api/users
Body: {
  "organization": "coromandel",
  "username": "newuser",
  "password": "password123",
  "role": "admin",
  "email": "user@example.com"  // optional
}
```

### Update User
```
PUT /api/users/{organization}:{username}
Body: {
  "role": "admin",           // optional
  "password": "newpass",     // optional
  "email": "new@email.com"   // optional
}
```

### Delete User
```
DELETE /api/users/{organization}:{username}
```

## User Storage

Users are stored in `users.json` (or `/home/site/data/users.json` on Azure):

```json
{
  "coromandel:admin": {
    "password": "$2b$12$...",
    "role": "admin",
    "organization": "coromandel",
    "username": "admin",
    "created_at": "2025-12-22T15:55:52.791722",
    "email": "admin@coromandel.com"
  }
}
```

## Integration with Easy Auth

If Azure Easy Auth is enabled:
- Users can be mapped to Easy Auth identities via `/auth/map-user`
- The User Management module shows all users (both local and Easy Auth mapped)
- Easy Auth users appear in the list once mapped to an organization

## Troubleshooting

### "Access denied" Error
- **Cause**: You're not logged in as a Dachido admin
- **Solution**: Log in with Dachido admin credentials

### "User already exists" Error
- **Cause**: Trying to create a user with an existing organization:username combination
- **Solution**: Use a different username or organization

### "Cannot delete your own account" Error
- **Cause**: Trying to delete the account you're currently logged in with
- **Solution**: Have another Dachido admin delete the account, or log in as a different user first

### Users Not Appearing
- **Cause**: API call failed or authentication issue
- **Solution**: 
  - Check browser console for errors
  - Verify you're logged in
  - Check network tab for API response

### Module Not Visible
- **Cause**: You're not a Dachido admin
- **Solution**: The module only appears for Dachido admins. Regular users and organization admins cannot see it.

## Best Practices

1. **Use Strong Passwords**: Always set strong passwords for new users
2. **Verify Organization Names**: Ensure organization names are spelled correctly (case-insensitive)
3. **Set Email Addresses**: Adding email addresses helps with Easy Auth mapping
4. **Regular Audits**: Periodically review the user list to remove inactive users
5. **Role Assignment**: Assign the minimum required role (don't make everyone Dachido admin)

## Future Enhancements

Potential improvements:
- Bulk user import/export
- User activity tracking
- Password reset functionality
- Organization-level admin user management
- User search and filtering
- Advanced role permissions

## Technical Details

### Frontend Implementation
- **Location**: `templates/dashboard.html`
- **Module ID**: `users-module`
- **JavaScript Function**: `loadUsersData()`
- **Rendering Function**: `renderUsersTable()`

### Backend Implementation
- **Routes**: `app.py` (lines 2043-2160)
- **Authentication**: `@login_required` + `@auth.require_dachido_admin`
- **Storage**: `auth.py` functions (`load_users()`, `save_users()`, `add_user()`)

### Data Flow
```
User clicks "USER MANAGEMENT" tab
    ↓
loadUsersData() called
    ↓
GET /api/users (with credentials)
    ↓
Backend validates Dachido admin role
    ↓
Returns user list from users.json
    ↓
renderUsersTable() displays users
    ↓
User actions (add/edit/delete)
    ↓
API calls to /api/users
    ↓
Backend updates users.json
    ↓
Frontend refreshes table
```

## Summary

The User Management feature provides a seamless, integrated experience for Dachido admins to manage users directly from the dashboard. It supports full CRUD operations (Create, Read, Update, Delete) with real-time updates and comprehensive error handling.

