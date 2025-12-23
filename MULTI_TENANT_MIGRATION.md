# Multi-Tenant Migration Guide

## Overview
The dashboard has been transformed from a single-tenant application to a multi-tenant SaaS platform supporting multiple organizations and Dachido admin access.

## Key Changes

### 1. Authentication System (`auth.py`)
- **JWT Token-Based Authentication**: Replaced session-based auth with JWT tokens stored in HTTP-only cookies
- **Organization-Based Users**: Users are now stored as `{organization}:{username}` format
- **30-Minute Token Expiration**: JWT tokens expire after 30 minutes
- **Organization Management**: Added functions to create and manage organizations
- **Dachido Admin Role**: Special `dachido_admin` role for super admins

### 2. Login Flow (`app.py` & `templates/login.html`)
- **Organization Field**: Login now requires organization + username + password
- **JWT Cookie**: On successful login, JWT token is set as HTTP-only cookie
- **Token Validation**: `@login_required` decorator validates JWT token and extracts user context
- **User Context**: User info (username, organization, role) stored in Flask `g` object

### 3. Dashboard Routing
- **Organization Dashboard**: Regular users see their organization-specific dashboard
- **Dachido Dashboard**: Dachido admins see Dachido dashboard (currently same template, can be customized)
- **Dynamic Organization Name**: Dashboard displays organization name from database, not hardcoded

### 4. Audio Monitor Filtering (`audio_monitor.py`)
- **Organization Filtering**: All audio recording queries filter by organization prefix
- **Blob Storage Convention**: Recordings stored as `{organization}/{filename}` in Azure Blob Storage
- **Dachido Access**: Dachido admins can see all recordings (no organization filter)

### 5. API Endpoints
- **Organization Context**: All protected endpoints have access to organization via `g.organization`
- **Data Isolation**: Audio recordings filtered by organization
- **Future-Ready**: Database queries can be filtered by organization when migrated to PostgreSQL

## File Structure

### New Files
- `requirements.txt` - Updated dependencies including PyJWT
- `organizations.json` - Stores organization metadata (created automatically)

### Modified Files
- `auth.py` - Complete rewrite for multi-tenant JWT authentication
- `app.py` - Updated login/logout, added organization context to all endpoints
- `templates/login.html` - Added organization field
- `templates/dashboard.html` - Dynamic organization name display
- `audio_monitor.py` - Organization filtering for all recording queries

## Default Users

On first run, the application creates:

1. **Dachido Admin**
   - Organization: `dachido`
   - Username: `admin`
   - Password: `adminpass`
   - Role: `dachido_admin`

2. **Coromandel Admin** (Sample Organization)
   - Organization: `coromandel`
   - Username: `admin`
   - Password: `adminpass`
   - Role: `admin`

3. **Coromandel Customer** (Sample Organization)
   - Organization: `coromandel`
   - Username: `customer`
   - Password: `customer123`
   - Role: `customer_admin`

## Usage

### Login
1. Navigate to the webapp URL
2. Enter:
   - **Organization**: `coromandel` (or your organization name)
   - **Username**: `admin` (or your username)
   - **Password**: `adminpass` (or your password)
3. JWT token is automatically stored in cookie (30-minute expiration)

### Creating New Organizations
Organizations can be created programmatically:
```python
auth.add_organization("neworg", display_name="New Organization")
auth.add_user("neworg", "admin", "password", role="admin")
```

Or through the registration endpoint (for Dachido admins).

## Azure Blob Storage Convention

Audio recordings must be stored with organization prefix:
- `coromandel/recording1.mp3`
- `coromandel/recording2.wav`
- `dachido/admin_recording.mp3` (for Dachido)

## Future Enhancements

### PostgreSQL Migration
When migrating to PostgreSQL:
1. Each organization can have its own database: `{organization}_db`
2. Or use schema-based isolation: `{organization}_schema`
3. Update `get_db_connection()` to select database based on organization

### Organization Customization
- **Logos**: Store organization logos and display in dashboard
- **Color Schemes**: CSS variables can be set per organization
- **Branding**: Customize dashboard title, footer, etc. per organization

### Database Schema Changes
When moving to PostgreSQL, consider:
- Adding `organization` column to all fact tables
- Adding organization foreign keys
- Creating organization-specific views

## Security Considerations

1. **JWT Secret Key**: Change `JWT_SECRET_KEY` in production (set via environment variable)
2. **HTTPS**: Cookies use `secure=True` in production
3. **Token Expiration**: 30-minute expiration balances security and UX
4. **Organization Validation**: Always validate organization from JWT token, never trust client input

## Testing

### Test Dachido Admin Login
```
Organization: dachido
Username: admin
Password: adminpass
```

### Test Organization User Login
```
Organization: coromandel
Username: customer
Password: customer123
```

## Migration Notes

### Existing Users
- Old format users (without organization) are automatically migrated on first login
- They are assigned to a default organization or need to be manually migrated

### Backward Compatibility
- Old user format is still supported for migration purposes
- Users are automatically converted to new format on login

## Environment Variables

```bash
# JWT Secret Key (REQUIRED in production)
JWT_SECRET_KEY=your_super_secret_jwt_key_change_in_production

# Flask Secret Key
SECRET_KEY=your_super_secret_key

# Azure Storage (for audio monitoring)
AZURE_STORAGE_CONNECTION_STRING=...
RECORDINGS_CONTAINER=recordings
PROCESSED_RECORDINGS_CONTAINER=processed-recordings
FAILED_RECORDINGS_CONTAINER=failedrecordings
TRANSCRIPTIONS_CONTAINER=transcriptions
```

## API Changes

### Authentication
- **Before**: Session-based (`session["logged_in"]`)
- **After**: JWT cookie-based (`auth_token` cookie)

### User Context
- **Before**: `session.get("username")`, `session.get("user_role")`
- **After**: `g.username`, `g.organization`, `g.role`

### Audio Endpoints
All audio endpoints now filter by organization automatically:
- `/api/audio/overview` - Shows stats for user's organization
- `/api/audio/pending` - Shows pending recordings for organization
- `/api/audio/processed` - Shows processed recordings for organization
- `/api/audio/failed` - Shows failed recordings for organization

## Troubleshooting

### "Invalid token" errors
- Token may have expired (30 minutes)
- Clear cookies and login again
- Check JWT_SECRET_KEY matches between restarts

### Can't see recordings
- Verify recordings are stored with organization prefix in Azure Blob Storage
- Check organization name matches exactly (case-sensitive)
- Dachido admins see all recordings regardless of prefix

### Organization not found
- Create organization using `auth.add_organization()`
- Check `organizations.json` file exists and has correct format

