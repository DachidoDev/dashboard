"""
Azure AD Authentication Module
Handles OAuth 2.0 authentication with Microsoft Azure AD
Uses app roles for role-based access control (RBAC)
"""

import os
import json
import jwt
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, redirect, url_for, session, make_response
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import msal

# Azure AD Configuration
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
AZURE_REDIRECT_URI = os.environ.get("AZURE_REDIRECT_URI", "")
AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your_super_secret_jwt_key_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8  # 8 hours token expiration

# Special organization for super admins
DACHIDO_ORG = "dachido"

# MSAL App Configuration
msal_app = None
if AZURE_CLIENT_ID and AZURE_TENANT_ID:
    msal_app = msal.ConfidentialClientApplication(
        client_id=AZURE_CLIENT_ID,
        client_credential=AZURE_CLIENT_SECRET,
        authority=AZURE_AUTHORITY
    )


def get_login_url():
    """Generate Azure AD login URL"""
    if not msal_app:
        raise ValueError("Azure AD not configured. Set AZURE_CLIENT_ID, AZURE_TENANT_ID, and AZURE_CLIENT_SECRET")
    
    # MSAL automatically adds 'openid' and 'profile' - don't include them explicitly
    # Only include custom scopes like 'User.Read' and 'email'
    auth_url = msal_app.get_authorization_request_url(
        scopes=["User.Read", "email"],
        redirect_uri=AZURE_REDIRECT_URI
    )
    return auth_url


def get_token_from_code(auth_code):
    """Exchange authorization code for access token"""
    if not msal_app:
        return None
    
    # MSAL automatically adds 'openid' and 'profile' - don't include them explicitly
    result = msal_app.acquire_token_by_authorization_code(
        code=auth_code,
        scopes=["User.Read", "email"],
        redirect_uri=AZURE_REDIRECT_URI
    )
    
    if "access_token" in result:
        return result["access_token"], result.get("id_token")
    else:
        print(f"⚠️  Token acquisition error: {result.get('error_description', result.get('error'))}")
        return None, None


def get_user_info_from_token(access_token):
    """Get user information from Microsoft Graph API"""
    graph_endpoint = "https://graph.microsoft.com/v1.0/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(graph_endpoint, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Graph API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"⚠️  Error fetching user info: {e}")
        return None


def get_app_roles_from_token(id_token):
    """Extract app roles from ID token"""
    try:
        # Decode token without verification (we'll verify with Azure)
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        roles = decoded.get("roles", [])
        return roles
    except Exception as e:
        print(f"⚠️  Error decoding token: {e}")
        return []


def map_role_to_organization_and_role(azure_roles):
    """
    Map Azure AD app roles to our internal organization and role system
    
    Azure AD App Roles:
    - dachido_admin → organization: "dachido", role: "dachido_admin"
    - customer_admin → organization: extracted from email domain or assigned
    - admin → organization: extracted from email domain or assigned
    
    Returns: (organization, role, username)
    """
    if not azure_roles:
        return None, None, None
    
    # Check for dachido_admin first (highest privilege)
    if "dachido_admin" in azure_roles:
        return "dachido", "dachido_admin", None
    
    # Check for admin
    if "admin" in azure_roles:
        # Organization will be determined from email domain or user assignment
        return None, "admin", None
    
    # Check for customer_admin
    if "customer_admin" in azure_roles:
        return None, "customer_admin", None
    
    return None, None, None


def extract_organization_from_email(email):
    """
    Extract organization name from email domain
    Example: user@coromandel.com → "coromandel"
    """
    if not email or "@" not in email:
        return None
    
    domain = email.split("@")[1].split(".")[0].lower()
    return domain


def generate_jwt_token(username, organization, role):
    """Generate JWT token for session management"""
    payload = {
        "username": username,
        "organization": organization,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token):
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return False, {"error": "Invalid token"}


def get_user_from_token():
    """
    Extract user information from JWT token in cookie
    Returns (username, organization, role) or (None, None, None) if invalid
    """
    token = request.cookies.get("auth_token")
    if not token:
        return None, None, None
    
    success, payload = verify_jwt_token(token)
    if not success:
        return None, None, None
    
    return payload.get("username"), payload.get("organization"), payload.get("role")


def is_dachido_admin(organization, role):
    """Check if user is a Dachido admin"""
    return organization == DACHIDO_ORG and role == "dachido_admin"


def require_auth(f):
    """
    Decorator to protect routes requiring authentication
    Validates JWT token and populates g object with user info
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username, organization, role = get_user_from_token()
        
        if not username or not organization:
            # Check if this is an API route
            if request.path.startswith("/api/"):
                from flask import jsonify
                return jsonify({"error": "Authentication required"}), 401
            # Redirect to login for web routes
            return redirect(url_for("azure_login"))
        
        # Populate Flask g object with user info
        g.username = username
        g.organization = organization
        g.role = role
        g.is_dachido_admin = is_dachido_admin(organization, role)
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(*allowed_roles):
    """
    Decorator to require specific role(s)
    Usage: @require_role("dachido_admin", "admin")
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            username, organization, role = get_user_from_token()
            
            if not username or not organization:
                if request.path.startswith("/api/"):
                    from flask import jsonify
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("azure_login"))
            
            if role not in allowed_roles:
                if request.path.startswith("/api/"):
                    from flask import jsonify
                    return jsonify({"error": "Insufficient permissions"}), 403
                from flask import render_template
                return render_template("error.html", error="Access denied. Insufficient permissions."), 403
            
            g.username = username
            g.organization = organization
            g.role = role
            g.is_dachido_admin = is_dachido_admin(organization, role)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_dachido_admin(f):
    """Decorator to require Dachido admin role"""
    return require_role("dachido_admin")(f)


def can_access_organization(user_org, target_org, user_role):
    """
    Check if user can access a specific organization's data
    - Dachido admins can access all organizations
    - Regular admins can only access their own organization
    """
    if user_role == "dachido_admin":
        return True
    return user_org == target_org


def has_permission(permission_name):
    """
    Check if user has a specific permission based on their role
    """
    permissions = {
        'dachido_admin': ['*'],  # All permissions
        'admin': ['view_dashboard', 'manage_users', 'view_analytics', 'manage_recordings'],
        'customer_admin': ['view_dashboard', 'view_analytics', 'view_recordings']
    }
    
    user_role = get_user_from_token()[2]  # Get role
    if not user_role:
        return False
    
    user_permissions = permissions.get(user_role, [])
    return '*' in user_permissions or permission_name in user_permissions

