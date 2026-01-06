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
    
    # Request User.Read for Graph API and email claim
    # OpenID Connect scopes (openid, profile, email) are added automatically by MSAL
    auth_url = msal_app.get_authorization_request_url(
        scopes=["User.Read"],  # This will include openid, profile, email automatically
        redirect_uri=AZURE_REDIRECT_URI
    )
    return auth_url


def get_token_from_code(auth_code):
    """Exchange authorization code for access token and ID token"""
    if not msal_app:
        return None, None
    
    # Acquire tokens using authorization code
    result = msal_app.acquire_token_by_authorization_code(
        code=auth_code,
        scopes=["User.Read"],  # Same scopes as login
        redirect_uri=AZURE_REDIRECT_URI
    )
    
    if "access_token" in result:
        access_token = result["access_token"]
        id_token = result.get("id_token")
        
        # Debug: Decode and inspect ID token
        if id_token:
            try:
                decoded = jwt.decode(id_token, options={"verify_signature": False})
                print(f"✅ Token acquired successfully")
                print(f"🔍 ID Token Claims: {list(decoded.keys())}")
                print(f"🔍 Has 'roles' claim: {'roles' in decoded}")
                print(f"🔍 Roles value: {decoded.get('roles', 'NOT FOUND')}")
                print(f"🔍 User: {decoded.get('email') or decoded.get('preferred_username') or decoded.get('upn')}")
                print(f"🔍 Name: {decoded.get('name')}")
                
                # If no roles, print diagnostic info
                if 'roles' not in decoded or not decoded.get('roles'):
                    print("⚠️  WARNING: No roles in ID token!")
                    print("⚠️  Check the following:")
                    print("   1. User has app role assigned in Enterprise Application → Users and groups")
                    print("   2. Wait 5-10 minutes after role assignment for propagation")
                    print("   3. User must sign out completely and sign back in")
                    print("   4. Clear browser cache and cookies")
            except Exception as e:
                print(f"⚠️  Could not decode ID token for debugging: {e}")
        
        return access_token, id_token
    else:
        error = result.get('error_description', result.get('error', 'Unknown error'))
        print(f"⚠️  Token acquisition error: {error}")
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
            user_data = response.json()
            print(f"✅ User info retrieved: {user_data.get('mail') or user_data.get('userPrincipalName')}")
            return user_data
        else:
            print(f"⚠️  Graph API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"⚠️  Error fetching user info: {e}")
        return None


def get_app_roles_from_token(id_token):
    """
    Extract app roles from ID token
    
    The 'roles' claim is automatically added to the ID token when:
    1. The user is assigned to an app role in the Enterprise Application
    2. The app requests the 'openid' scope (which MSAL does by default)
    """
    try:
        # Decode token without verification (Azure AD already verified it)
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        
        # Extract roles claim
        roles = decoded.get("roles", [])
        
        print(f"🔍 Extracting roles from ID token...")
        print(f"🔍 Found roles: {roles if roles else 'NONE'}")
        
        if not roles:
            print("⚠️  ========================================")
            print("⚠️  NO ROLES FOUND IN ID TOKEN!")
            print("⚠️  ========================================")
            print("⚠️  This usually means:")
            print("⚠️  1. User has no app role assignment")
            print("⚠️     → Go to: Enterprise Application → Users and groups → Assign role")
            print("⚠️  2. Role assignment hasn't propagated yet")
            print("⚠️     → Wait 5-10 minutes, then sign out and sign back in")
            print("⚠️  3. User needs to clear session")
            print("⚠️     → Sign out from Microsoft completely, clear cookies")
            print("⚠️  ========================================")
            
            # Print all available claims for debugging
            print(f"🔍 All claims in token: {list(decoded.keys())}")
        
        return roles
    except Exception as e:
        print(f"❌ Error decoding token: {e}")
        import traceback
        traceback.print_exc()
        return []


def map_role_to_organization_and_role(azure_roles):
    """
    Map Azure AD app roles to our internal organization and role system
    
    Azure AD App Roles (must match "Value" field in App Registration → App roles):
    - dachido_admin → organization: "dachido", role: "dachido_admin"
    - admin → organization: extracted from email domain
    - customer_admin → organization: extracted from email domain
    
    Returns: (organization, role, is_dachido_admin)
    """
    print(f"🔍 Mapping Azure roles: {azure_roles}")
    
    if not azure_roles:
        print("⚠️  No Azure roles to map!")
        return None, None, False
    
    # Take the first role (users should only have one app role assigned)
    primary_role = azure_roles[0] if isinstance(azure_roles, list) else azure_roles
    
    print(f"🔍 Primary role: {primary_role}")
    
    # Map based on role value (these MUST match your App Role "Value" field exactly)
    if primary_role == "dachido_admin":
        print("✅ Mapped to: dachido_admin")
        return "dachido", "dachido_admin", True
    elif primary_role == "admin":
        print("✅ Mapped to: admin (organization from email)")
        return None, "admin", False
    elif primary_role == "customer_admin":
        print("✅ Mapped to: customer_admin (organization from email)")
        return None, "customer_admin", False
    else:
        print(f"⚠️  Unknown role: {primary_role}")
        return None, None, False


def extract_organization_from_email(email):
    """
    Extract organization name from email domain
    Examples:
    - admin@coromandel.com → "coromandel"
    - user@philipderbekodachido.onmicrosoft.com → "dachido" (special handling)
    - admin@company.co.in → "company"
    """
    if not email or "@" not in email:
        print(f"⚠️  Invalid email format: {email}")
        return "default"
    
    domain = email.split("@")[1]
    
    # Special handling for Microsoft domains
    if "onmicrosoft.com" in domain:
        # philipderbekodachido.onmicrosoft.com → check if contains "dachido"
        org_part = domain.split(".")[0].lower()
        if "dachido" in org_part:
            print(f"✅ Extracted organization: dachido (from {email})")
            return "dachido"
        print(f"✅ Extracted organization: {org_part} (from {email})")
        return org_part
    
    # For regular domains, take the first part before the TLD
    # coromandel.com → coromandel
    org = domain.split(".")[0].lower()
    print(f"✅ Extracted organization: {org} (from {email})")
    return org


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