#!/usr/bin/env python3
"""
Migration Cleanup Script
Creates backups of authentication files before Azure AD migration
"""

import os
import shutil
import json
from datetime import datetime

BACKUP_DIR = "backup_pre_azure_migration"
FILES_TO_BACKUP = [
    "users.json",
    "organizations.json",
    "user_mappings.json",
    "auth.py",
    "easy_auth.py"
]

def create_backup_directory():
    """Create backup directory with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{BACKUP_DIR}_{timestamp}"
    
    if os.path.exists(backup_path):
        print(f"Backup directory already exists: {backup_path}")
        response = input("Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Backup cancelled")
            return None
        shutil.rmtree(backup_path)
    
    os.makedirs(backup_path, exist_ok=True)
    print(f"Created backup directory: {backup_path}")
    return backup_path

def backup_file(file_path, backup_dir):
    """Backup a single file if it exists"""
    if os.path.exists(file_path):
        dest_path = os.path.join(backup_dir, os.path.basename(file_path))
        shutil.copy2(file_path, dest_path)
        print(f"Backed up: {file_path} -> {dest_path}")
        return True
    else:
        print(f"File not found (skipping): {file_path}")
        return False

def export_users_summary(backup_dir):
    """Export a summary of users.json for reference"""
    users_file = "users.json"
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r') as f:
                users = json.load(f)
            
            summary = {
                "exported_at": datetime.now().isoformat(),
                "total_users": len(users),
                "users": []
            }
            
            for user_key, user_data in users.items():
                if isinstance(user_data, dict):
                    summary["users"].append({
                        "key": user_key,
                        "organization": user_data.get("organization", ""),
                        "username": user_data.get("username", ""),
                        "role": user_data.get("role", ""),
                        "email": user_data.get("email", ""),
                        "created_at": user_data.get("created_at", "")
                    })
                else:
                    # Legacy format (just password hash)
                    summary["users"].append({
                        "key": user_key,
                        "format": "legacy",
                        "note": "Password hash only, no metadata"
                    })
            
            summary_file = os.path.join(backup_dir, "users_summary.json")
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            print(f"Exported users summary: {summary_file}")
            print(f"   Total users: {summary['total_users']}")
            
        except Exception as e:
            print(f"Error exporting users summary: {e}")

def create_migration_readme(backup_dir):
    """Create a README in backup directory explaining the migration"""
    readme_content = f"""# Pre-Azure AD Migration Backup

**Backup Created:** {datetime.now().isoformat()}

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
   cp {backup_dir}/* .
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
"""
    
    readme_file = os.path.join(backup_dir, "README.md")
    # Use UTF-8 encoding to support all characters
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"Created backup README: {readme_file}")

def main():
    """Main backup function"""
    print("=" * 60)
    print("Azure AD Migration - Pre-Deployment Backup")
    print("=" * 60)
    print()
    
    # Create backup directory
    backup_dir = create_backup_directory()
    if not backup_dir:
        return
    
    print()
    print("Backing up files...")
    print("-" * 60)
    
    # Backup files
    backed_up_count = 0
    for file_path in FILES_TO_BACKUP:
        if backup_file(file_path, backup_dir):
            backed_up_count += 1
    
    print()
    print(f"Backed up {backed_up_count} file(s)")
    print()
    
    # Export users summary
    print("Exporting users summary...")
    print("-" * 60)
    export_users_summary(backup_dir)
    
    print()
    print("Creating backup documentation...")
    print("-" * 60)
    create_migration_readme(backup_dir)
    
    print()
    print("=" * 60)
    print("Backup Complete!")
    print("=" * 60)
    print()
    print(f"Backup location: {backup_dir}")
    print()
    print("Next steps:")
    print("1. Review users_summary.json for user mapping")
    print("2. Create users in Azure AD")
    print("3. Assign users to app roles")
    print("4. Set environment variables in Azure App Service")
    print("5. Deploy code")
    print()
    print("WARNING: Keep this backup until migration is confirmed successful!")

if __name__ == "__main__":
    main()

