# How to Set Startup Command in Azure Portal

## Step-by-Step Instructions

### 1. Navigate to Your Web App
- Go to [Azure Portal](https://portal.azure.com)
- Find and click on your **Web App** (not App Service Plan)

### 2. Go to Configuration
- In the left sidebar, under **Settings**, click on **"Configuration"**
- **NOT** "Platform settings" - that's different!

### 3. Go to General Settings Tab
- At the top, you'll see tabs: **Application Settings**, **General Settings**, **Path mappings**, etc.
- Click on **"General Settings"** tab

### 4. Set Startup Command
- Scroll down to find **"Startup Command"** field
- Enter this command:
  ```
  gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 --threads 4 --access-logfile - --error-logfile - app:app
  ```

### 5. Save and Restart
- Click **"Save"** at the top
- Azure will ask if you want to restart - click **"Continue"** or **"Yes"**
- Wait for the restart to complete (usually 1-2 minutes)

## Visual Path

```
Azure Portal
  └── Your Web App
      └── Settings (left sidebar)
          └── Configuration
              └── General Settings (tab at top)
                  └── Startup Command (field)
```

## Alternative: Via Azure CLI

If you prefer command line:

```bash
az webapp config set \
  --name <your-app-name> \
  --resource-group <your-resource-group> \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 --threads 4 --access-logfile - --error-logfile - app:app"
```

## What Each Parameter Means

- `--bind=0.0.0.0:8000`: Listen on all interfaces, port 8000
- `--timeout 600`: Request timeout (10 minutes)
- `--workers 2`: Number of worker processes
- `--threads 4`: Threads per worker
- `--access-logfile -`: Log access to stdout
- `--error-logfile -`: Log errors to stdout
- `app:app`: Flask app object (app.py → app variable)

## After Setting

1. **Remove the startup command step** from your GitHub Actions workflow (optional but recommended)
2. **Test your deployment** - it should work without SCM restart conflicts
3. **Check logs** to verify the app starts correctly:
   ```bash
   az webapp log tail --name <your-app-name> --resource-group <your-resource-group>
   ```

## Troubleshooting

### Can't find "General Settings" tab?
- Make sure you're in **Configuration** (not Platform settings)
- Look at the tabs at the top of the Configuration page
- If you don't see it, your Web App might be Windows-based (this is for Linux)

### Command not working?
- Check that `gunicorn` is in your `requirements.txt`
- Verify Python version is 3.10
- Check application logs for errors

### App still not starting?
- Verify the startup command is saved (refresh the page)
- Check that the app restarted after saving
- Review application logs for startup errors

