# Pre-Azure AD Migration Backup

**Backup Created:** 2026-01-04T18:42:34.228119

## Contents

This backup contains authentication files before migrating to Azure AD authentication.

### Files Backed Up:
- `users.json` - Local user accounts (username/password)
- `organizations.json` - Organization metadata
- `user_mappings.json` - Easy Auth user mappings (if exists)
- `auth.py` - Local authentication module
- `easy_auth.py` - Azure Easy Auth integration module

### Migration Details

**From:** Local username/password authentication
**To:** Azure AD (Microsoft Entra ID) with app roles

### User Mapping Reference

See `users_summary.json` for a list of all users that need to be:
1. Created in Azure AD
2. Assigned to appropriate app roles

### Rollback Instructions

If you need to rollback:

1. Restore files from this backup:
   ```bash
   cp backup_pre_azure_migration_20260104_184234/* .
   ```

2. Remove Azure AD environment variables from Azure App Service

3. Restore code from git:
   ```bash
   git checkout pre-azure-ad-migration
   ```

### Important Notes

- WARNING: **Do not delete this backup** until migration is confirmed successful
- WARNING: **users.json contains password hashes** - keep secure
- WARNING: **Test Azure AD authentication thoroughly** before removing backups
