#!/bin/bash

# Azure AD Environment Setup Script
# Sets environment variables in Azure App Service

set -e

echo "=========================================="
echo "Azure AD Environment Configuration"
echo "=========================================="
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
echo "Checking Azure login..."
if ! az account show &> /dev/null; then
    echo "⚠️  Not logged in to Azure. Please login:"
    az login
fi

echo "✅ Azure CLI ready"
echo ""

# Get inputs
read -p "Enter Azure Client ID: " AZURE_CLIENT_ID
read -sp "Enter Azure Client Secret: " AZURE_CLIENT_SECRET
echo ""
read -p "Enter Azure Tenant ID: " AZURE_TENANT_ID
read -p "Enter App Service name: " APP_SERVICE_NAME
read -p "Enter Resource Group name: " RESOURCE_GROUP

# Generate JWT secret
echo ""
echo "Generating JWT secret..."
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)

if [ -z "$JWT_SECRET" ]; then
    echo "⚠️  Could not generate JWT secret automatically"
    read -sp "Enter JWT Secret Key (32+ characters): " JWT_SECRET
    echo ""
fi

# Construct redirect URI
REDIRECT_URI="https://${APP_SERVICE_NAME}.azurewebsites.net/auth/callback"

echo ""
echo "Configuration Summary:"
echo "  Client ID: ${AZURE_CLIENT_ID}"
echo "  Tenant ID: ${AZURE_TENANT_ID}"
echo "  App Service: ${APP_SERVICE_NAME}"
echo "  Resource Group: ${RESOURCE_GROUP}"
echo "  Redirect URI: ${REDIRECT_URI}"
echo ""

read -p "Continue with configuration? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "❌ Configuration cancelled"
    exit 1
fi

echo ""
echo "Setting environment variables in Azure App Service..."
echo ""

# Set environment variables
az webapp config appsettings set \
    --name "$APP_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings \
    AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
    AZURE_CLIENT_SECRET="$AZURE_CLIENT_SECRET" \
    AZURE_TENANT_ID="$AZURE_TENANT_ID" \
    AZURE_REDIRECT_URI="$REDIRECT_URI" \
    JWT_SECRET_KEY="$JWT_SECRET" \
    --output none

if [ $? -eq 0 ]; then
    echo "✅ Environment variables set successfully"
else
    echo "❌ Failed to set environment variables"
    exit 1
fi

echo ""
echo "Restarting App Service..."
az webapp restart \
    --name "$APP_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output none

if [ $? -eq 0 ]; then
    echo "✅ App Service restarted"
else
    echo "⚠️  Failed to restart App Service (restart manually)"
fi

echo ""
echo "Creating .env file for local development..."
cat > .env << EOF
# Azure AD Configuration
AZURE_CLIENT_ID=$AZURE_CLIENT_ID
AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET
AZURE_TENANT_ID=$AZURE_TENANT_ID
AZURE_REDIRECT_URI=http://localhost:5000/auth/callback
JWT_SECRET_KEY=$JWT_SECRET
EOF

echo "✅ Created .env file"
echo ""
echo "=========================================="
echo "✅ Configuration Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify environment variables in Azure Portal"
echo "2. Test login at: https://${APP_SERVICE_NAME}.azurewebsites.net/login"
echo "3. Check logs in Azure Portal → Log stream"
echo ""
echo "⚠️  Keep .env file secure and add to .gitignore!"

