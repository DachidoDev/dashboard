# Azure AD Environment Setup Script (PowerShell)
# Sets environment variables in Azure App Service

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Azure AD Environment Configuration" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Azure CLI is installed
try {
    $null = Get-Command az -ErrorAction Stop
} catch {
    Write-Host "❌ Azure CLI is not installed" -ForegroundColor Red
    Write-Host "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check if logged in to Azure
Write-Host "Checking Azure login..."
try {
    $null = az account show 2>$null
    Write-Host "✅ Azure CLI ready" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Not logged in to Azure. Please login:" -ForegroundColor Yellow
    az login
}

Write-Host ""

# Get inputs
$AZURE_CLIENT_ID = Read-Host "Enter Azure Client ID"
$AZURE_CLIENT_SECRET = Read-Host "Enter Azure Client Secret" -AsSecureString
$AZURE_CLIENT_SECRET_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($AZURE_CLIENT_SECRET)
)
$AZURE_TENANT_ID = Read-Host "Enter Azure Tenant ID"
$APP_SERVICE_NAME = Read-Host "Enter App Service name"
$RESOURCE_GROUP = Read-Host "Enter Resource Group name"

# Generate JWT secret
Write-Host ""
Write-Host "Generating JWT secret..."
try {
    $JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(32))" 2>$null
    if (-not $JWT_SECRET) {
        $JWT_SECRET = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    }
} catch {
    Write-Host "⚠️  Could not generate JWT secret automatically" -ForegroundColor Yellow
    $JWT_SECRET = Read-Host "Enter JWT Secret Key (32+ characters)"
}

# Construct redirect URI
$REDIRECT_URI = "https://${APP_SERVICE_NAME}.azurewebsites.net/auth/callback"

Write-Host ""
Write-Host "Configuration Summary:"
Write-Host "  Client ID: $AZURE_CLIENT_ID"
Write-Host "  Tenant ID: $AZURE_TENANT_ID"
Write-Host "  App Service: $APP_SERVICE_NAME"
Write-Host "  Resource Group: $RESOURCE_GROUP"
Write-Host "  Redirect URI: $REDIRECT_URI"
Write-Host ""

$CONFIRM = Read-Host "Continue with configuration? (y/n)"
if ($CONFIRM -ne "y") {
    Write-Host "❌ Configuration cancelled" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setting environment variables in Azure App Service..."
Write-Host ""

# Set environment variables
az webapp config appsettings set `
    --name "$APP_SERVICE_NAME" `
    --resource-group "$RESOURCE_GROUP" `
    --settings `
    AZURE_CLIENT_ID="$AZURE_CLIENT_ID" `
    AZURE_CLIENT_SECRET="$AZURE_CLIENT_SECRET_PLAIN" `
    AZURE_TENANT_ID="$AZURE_TENANT_ID" `
    AZURE_REDIRECT_URI="$REDIRECT_URI" `
    JWT_SECRET_KEY="$JWT_SECRET" `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Environment variables set successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to set environment variables" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Restarting App Service..."
az webapp restart `
    --name "$APP_SERVICE_NAME" `
    --resource-group "$RESOURCE_GROUP" `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ App Service restarted" -ForegroundColor Green
} else {
    Write-Host "⚠️  Failed to restart App Service (restart manually)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Creating .env file for local development..."
$envContent = @"
# Azure AD Configuration
AZURE_CLIENT_ID=$AZURE_CLIENT_ID
AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET_PLAIN
AZURE_TENANT_ID=$AZURE_TENANT_ID
AZURE_REDIRECT_URI=http://localhost:5000/auth/callback
JWT_SECRET_KEY=$JWT_SECRET
"@

$envContent | Out-File -FilePath ".env" -Encoding utf8
Write-Host "✅ Created .env file" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Configuration Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Verify environment variables in Azure Portal"
Write-Host "2. Test login at: https://${APP_SERVICE_NAME}.azurewebsites.net/login"
Write-Host "3. Check logs in Azure Portal → Log stream"
Write-Host ""
Write-Host "⚠️  Keep .env file secure and add to .gitignore!" -ForegroundColor Yellow

