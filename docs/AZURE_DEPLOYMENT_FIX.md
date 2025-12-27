# Azure Deployment Fix - Internal Server Error

## Issues Fixed

### 1. **Startup Command Not Set**
- **Problem**: GitHub Actions workflow wasn't setting the startup command in Azure
- **Fix**: Added step to set startup command via Azure CLI

### 2. **Missing Directories**
- **Problem**: `/home/site/data/` directory might not exist, causing file creation errors
- **Fix**: Added directory creation logic in:
  - `auth.py` (for users.json and organizations.json)
  - `app.py` (for database file)

### 3. **Duplicate Dependencies**
- **Problem**: `python-dotenv` appeared twice in requirements.txt
- **Fix**: Removed duplicate entry

### 4. **Initialization Errors**
- **Problem**: App initialization code in `if __name__ == "__main__"` doesn't run in production
- **Fix**: Moved initialization to module level with error handling

## Required Azure App Settings

Make sure these are set in Azure Portal → Your Web App → Configuration → Application Settings:

```
JWT_SECRET_KEY=<your-strong-secret-key>
SECRET_KEY=<your-flask-secret-key>
AZURE_STORAGE_CONNECTION_STRING=<your-azure-storage-connection-string>
RECORDINGS_CONTAINER=recordings
PROCESSED_RECORDINGS_CONTAINER=processed-recordings
FAILED_RECORDINGS_CONTAINER=failedrecordings
TRANSCRIPTIONS_CONTAINER=transcriptions
FLASK_ENV=production
WEBSITE_INSTANCE_ID=<automatically-set-by-azure>
```

## Required GitHub Secrets

In your GitHub repository → Settings → Secrets and variables → Actions:

1. `AZURE_CREDENTIALS` - Service principal credentials (JSON)
2. `AZURE_WEBAPP_NAME` - Your Azure Web App name
3. `AZURE_RESOURCE_GROUP` - Your Azure resource group name

## How to Get Azure Credentials

```bash
# Create service principal
az ad sp create-for-rbac --name "github-actions-deploy" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
  --sdk-auth

# Copy the JSON output and add it as AZURE_CREDENTIALS secret
```

## Testing the Deployment

1. **Check Logs**:
   ```bash
   az webapp log tail --name <your-app-name> --resource-group <your-resource-group>
   ```

2. **SSH into App**:
   ```bash
   az webapp ssh --name <your-app-name> --resource-group <your-resource-group>
   ```

3. **Check Files**:
   ```bash
   ls -la /home/site/data/
   # Should see: fieldforce.db, users.json, organizations.json
   ```

## Common Issues

### Issue: "Module not found"
- **Solution**: Ensure all dependencies are in `requirements.txt`
- Check that `gunicorn` is installed

### Issue: "Permission denied"
- **Solution**: Azure Web App has write permissions to `/home/site/data/`
- This is automatically configured

### Issue: "Database locked"
- **Solution**: SQLite might have locking issues with multiple workers
- Consider using PostgreSQL for production (future migration)

### Issue: "JWT token errors"
- **Solution**: Ensure `JWT_SECRET_KEY` is set in Azure App Settings
- Must be a strong, random string

## Startup Command

The startup command is now set automatically:
```bash
gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 --threads 4 --access-logfile - --error-logfile - app:app
```

**Parameters**:
- `--workers 2`: Number of worker processes (adjust based on your plan)
- `--threads 4`: Threads per worker
- `--timeout 600`: Request timeout (10 minutes)
- `--access-logfile -`: Log to stdout
- `--error-logfile -`: Error log to stdout

## Next Steps

1. Push these changes to your `main` branch
2. GitHub Actions will automatically deploy
3. Check Azure logs for any errors
4. Test the application URL

