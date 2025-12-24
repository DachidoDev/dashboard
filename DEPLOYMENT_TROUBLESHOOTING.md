# Deployment Troubleshooting Guide

## Issue: SCM Container Restart During Deployment

### Error Message
```
Deployment has been stopped due to SCM container restart. 
The restart can happen due to a management operation on site. 
Do not perform a management operation and a deployment operation in quick succession.
```

### Root Cause
Setting the startup command via `az webapp config set` causes the SCM (Source Control Manager) container to restart. If deployment happens immediately after, it conflicts with the restart.

### Solution
**Option 1: Set startup command AFTER deployment** (Current workflow)
- Deploy first, then set startup command
- This avoids the conflict

**Option 2: Set startup command manually in Azure Portal** (Recommended for production)
1. Go to Azure Portal → Your Web App → Configuration → General Settings
2. Set "Startup Command" to:
   ```
   gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 --threads 4 --access-logfile - --error-logfile - app:app
   ```
3. Save and restart the app
4. Remove the "Set startup command" step from the workflow

**Option 3: Use Azure App Service Configuration**
- Set startup command via Azure CLI in a separate workflow/job
- Or set it once manually and never change it in CI/CD

## Issue: Virtual Environment Creation Fails

### Error Message
```
Creating virtual environment...
Error: Failed to deploy web package to App Service.
```

### Possible Causes
1. **Insufficient resources**: App Service plan too small
2. **Python version mismatch**: Check Azure Web App Python version
3. **Missing dependencies**: Check requirements.txt

### Solutions
1. **Check App Service Plan**: Ensure you have at least Basic tier (not Free)
2. **Verify Python Version**: 
   ```bash
   az webapp config show --name <app-name> --resource-group <rg-name> --query linuxFxVersion
   ```
   Should show: `Python|3.10`
3. **Set Python version explicitly**:
   ```bash
   az webapp config set --name <app-name> --resource-group <rg-name> --linux-fx-version "Python|3.10"
   ```

## Issue: Build Fails During Oryx Build

### Check Build Logs
1. Go to Azure Portal → Your Web App → Deployment Center → Logs
2. Look for specific error messages
3. Common issues:
   - Missing dependencies in requirements.txt
   - Syntax errors in Python code
   - Import errors

### Solutions
1. **Test locally first**:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

2. **Check for missing dependencies**: Ensure all imports are in requirements.txt

3. **Verify file structure**: Ensure app.py is in the root directory

## Issue: Application Not Starting

### Check Application Logs
```bash
az webapp log tail --name <app-name> --resource-group <rg-name>
```

### Common Issues
1. **Port binding**: App must bind to port from `PORT` environment variable or 8000
2. **Missing environment variables**: Check Azure App Settings
3. **Database path**: Ensure `/home/site/data/` directory exists

### Solutions
1. **Check startup command**: Verify it's set correctly
2. **Check environment variables**: Ensure all required vars are set
3. **Check file permissions**: Azure should handle this automatically

## Recommended Workflow Structure

### For Production
1. **Set startup command once manually** in Azure Portal
2. **Remove startup command step** from CI/CD workflow
3. **Only deploy code** in the workflow

### For Development
1. Keep the current workflow (sets startup command after deployment)
2. Monitor for SCM restart conflicts
3. Add delays if needed

## Manual Startup Command Setup

### Via Azure Portal
1. Azure Portal → Your Web App
2. Settings → Configuration → General Settings
3. Startup Command:
   ```
   gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 --threads 4 --access-logfile - --error-logfile - app:app
   ```
4. Save → Restart app

### Via Azure CLI
```bash
az webapp config set \
  --name <your-app-name> \
  --resource-group <your-resource-group> \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 --threads 4 --access-logfile - --error-logfile - app:app"
```

## Quick Fixes

### If deployment keeps failing:
1. **Wait 5 minutes** between management operations
2. **Set startup command manually** in Azure Portal
3. **Remove startup command step** from workflow
4. **Redeploy**

### If app doesn't start:
1. **Check logs**: `az webapp log tail`
2. **Verify startup command** is set
3. **Check environment variables**
4. **Verify Python version** matches (3.10)

