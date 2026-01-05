# Azure AD Deployment Quick Start

## Quick Setup (5 minutes)

### 1. Run Backup Script

```bash
python migration_cleanup.py
```

This creates a backup of all authentication files before migration.

### 2. Run Setup Script

**Windows (PowerShell):**
```powershell
.\setup_env.ps1
```

**Linux/Mac:**
```bash
chmod +x setup_env.sh
./setup_env.sh
```

The script will:
- Prompt for Azure AD credentials
- Generate JWT secret
- Set environment variables in Azure App Service
- Restart the app
- Create `.env` file for local development

### 3. Deploy Code

```bash
git add .
git commit -m "Migrate to Azure AD authentication"
git push origin main
```

### 4. Test Login

Visit: `https://your-app.azurewebsites.net/login`

---

## Prerequisites

Before running setup scripts, ensure you have:

1. ✅ **Azure AD App Registration created** (see migration guide)
2. ✅ **Client ID, Client Secret, Tenant ID** ready
3. ✅ **Azure CLI installed** and logged in
4. ✅ **App Service name** and **Resource Group name**

---

## Detailed Documentation

- **Full Migration Guide**: `docs/AZURE_AD_MIGRATION_GUIDE.md`
- **Deployment Checklist**: `docs/AZURE_AD_DEPLOYMENT_CHECKLIST.md`

---

## Troubleshooting

### Script fails with "Azure CLI not found"
Install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

### Script fails with "Not logged in"
Run: `az login`

### Environment variables not set
Check Azure Portal → App Service → Configuration → Application settings

### Login redirects but fails
- Verify redirect URI matches exactly
- Check client secret is correct
- Verify API permissions are granted

---

## Support

For detailed troubleshooting, see the migration guide troubleshooting section.

