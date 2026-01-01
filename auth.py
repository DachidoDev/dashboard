"""
Multi-tenant authentication module with JWT support
Supports organization-based user management and Dachido admin access
"""
import json
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, redirect, url_for
from flask_bcrypt import Bcrypt

# Bcrypt will be initialized by the Flask app
bcrypt = Bcrypt()

USERS_FILE = "users.json"
ORGANIZATIONS_FILE = "organizations.json"
if os.environ.get("WEBSITE_INSTANCE_ID"):  # Running on Azure
    USERS_FILE = "/home/site/data/users.json"
    ORGANIZATIONS_FILE = "/home/site/data/organizations.json"

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your_super_secret_jwt_key_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30

# Special organization for super admins
DACHIDO_ORG = "dachido"


def load_users():
    """Load users from JSON file"""
    # Ensure directory exists (for Azure deployment)
    users_dir = os.path.dirname(USERS_FILE)
    if users_dir and not os.path.exists(users_dir):
        os.makedirs(users_dir, exist_ok=True)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def load_organizations():
    """Load organizations from JSON file"""
    # Ensure directory exists (for Azure deployment)
    orgs_dir = os.path.dirname(ORGANIZATIONS_FILE)
    if orgs_dir and not os.path.exists(orgs_dir):
        os.makedirs(orgs_dir, exist_ok=True)
    
    if not os.path.exists(ORGANIZATIONS_FILE):
        with open(ORGANIZATIONS_FILE, "w") as f:
            json.dump({}, f)
    with open(ORGANIZATIONS_FILE, "r") as f:
        return json.load(f)


def save_organizations(organizations):
    """Save organizations to JSON file"""
    with open(ORGANIZATIONS_FILE, "w") as f:
        json.dump(organizations, f, indent=4)


def add_organization(org_name, display_name=None, metadata=None):
    """
    Add a new organization
    Returns True if added, False if already exists
    """
    organizations = load_organizations()
    if org_name in organizations:
        return False
    
    organizations[org_name] = {
        "display_name": display_name or org_name.title(),
        "created_at": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    save_organizations(organizations)
    return True


def get_organization(org_name):
    """Get organization information"""
    organizations = load_organizations()
    return organizations.get(org_name)


def add_user(organization, username, password, role="customer_admin"):
    """
    Add a new user with organization and role
    role can be: 'dachido_admin', 'admin', or 'customer_admin'
    """
    users = load_users()
    user_key = f"{organization}:{username}"
    
    if user_key in users:
        return False  # User already exists
    
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
    users[user_key] = {
        "password": hashed_password,
        "role": role,
        "organization": organization,
        "username": username,
        "created_at": datetime.now().isoformat()
    }
    save_users(users)
    return True


def check_password(organization, username, password):
    """
    Check password and return (success, role, organization) tuple
    """
    users = load_users()
    user_key = f"{organization}:{username}"
    
    if user_key not in users:
        return False, None, None
    
    user_data = users[user_key]
    
    # Handle old format (backward compatibility)
    if isinstance(user_data, str):
        # Old format: just the hashed password string
        if bcrypt.check_password_hash(user_data, password):
            # Migrate to new format - assume admin role for old users
            users[user_key] = {
                "password": user_data,
                "role": "admin",
                "organization": organization,
                "username": username,
                "created_at": datetime.now().isoformat()
            }
            save_users(users)
            return True, "admin", organization
        return False, None, None
    
    # New format: dict with password and role
    if bcrypt.check_password_hash(user_data["password"], password):
        role = user_data.get("role", "customer_admin")
        org = user_data.get("organization", organization)
        return True, role, org
    
    return False, None, None


def generate_jwt_token(username, organization, role):
    """
    Generate JWT token with user information
    Token expires in 30 minutes
    """
    expiration = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    
    payload = {
        "username": username,
        "organization": organization,
        "role": role,
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    # jwt.encode returns a string in PyJWT 2.x, but ensure it's a string
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token


def verify_jwt_token(token):
    """
    Verify and decode JWT token
    Returns (success, payload) tuple
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return False, {"error": "Invalid token"}


def get_user_from_token():
    """
    Extract user information from JWT token in cookie or Easy Auth
    Returns (username, organization, role) or (None, None, None) if invalid
    
    Priority:
    1. Try Easy Auth (if enabled)
    2. Fall back to JWT token in cookie
    """
    # Try Easy Auth first (if enabled)
    try:
        from easy_auth import is_easy_auth_enabled, get_user_from_easy_auth
        
        if is_easy_auth_enabled():
            username, organization, role = get_user_from_easy_auth()
            if username and organization:
                print(f"✅ Easy Auth user: {organization}:{username} (role: {role})")
                return username, organization, role
    except ImportError:
        # easy_auth module not available, continue with JWT
        pass
    except Exception as e:
        print(f"⚠️  Easy Auth error: {e}")
        # Fall through to JWT token check
    
    # Fall back to JWT token in cookie
    token = request.cookies.get("auth_token")
    if not token:
        print("⚠️  No auth_token cookie found in request")
        print(f"⚠️  Available cookies: {list(request.cookies.keys())}")
        return None, None, None
    
    print(f"✅ Found auth_token cookie: {token[:50]}...")  # Debug: show first 50 chars
    success, payload = verify_jwt_token(token)
    if not success:
        print(f"⚠️  Token verification failed: {payload}")
        return None, None, None
    
    print(f"✅ Token verified successfully for: {payload.get('organization')}:{payload.get('username')}")
    return payload.get("username"), payload.get("organization"), payload.get("role")


def is_dachido_admin(organization, role):
    """Check if user is a Dachido admin"""
    return organization == DACHIDO_ORG and role == "dachido_admin"


def login_required(f):
    """
    Decorator to protect routes requiring authentication
    Validates JWT token and populates g object with user info
    For API routes, returns JSON error instead of redirecting
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username, organization, role = get_user_from_token()
        
        if not username or not organization:
            # Check if this is an API route (starts with /api/)
            if request.path.startswith('/api/'):
                from flask import jsonify
                return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            # For non-API routes, redirect to login
            return redirect(url_for("login"))
        
        # Store user info in Flask's g object for use in the request
        g.username = username
        g.organization = organization
        g.role = role
        g.is_dachido_admin = is_dachido_admin(organization, role)
        
        # Debug logging for API routes
        if request.path.startswith('/api/'):
            print(f"🔐 API Request - User: {username}, Org: {organization}, Role: {role}, Is Dachido Admin: {g.is_dachido_admin}")
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_user_role(organization, username):
    """Get the role of a user"""
    users = load_users()
    user_key = f"{organization}:{username}"
    
    if user_key not in users:
        return None
    
    user_data = users[user_key]
    if isinstance(user_data, str):
        return "admin"  # Default for old format
    return user_data.get("role", "customer_admin")


def init_auth(app):
    """Initialize authentication with Flask app"""
    bcrypt.init_app(app)
    # Set JWT secret key from app config if available
    global JWT_SECRET_KEY
    JWT_SECRET_KEY = app.config.get("SECRET_KEY", JWT_SECRET_KEY)


# ============================================================================
# RBAC (Role-Based Access Control) Helpers
# ============================================================================

def require_role(*allowed_roles):
    """
    Decorator to require specific roles
    Usage: @require_role('dachido_admin', 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'role'):
                if request.path.startswith('/api/'):
                    from flask import jsonify
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("login"))
            
            if g.role not in allowed_roles:
                if request.path.startswith('/api/'):
                    from flask import jsonify
                    return jsonify({"error": "Insufficient permissions"}), 403
                return redirect(url_for("index"))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_dachido_admin(f):
    """Decorator to require Dachido admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'is_dachido_admin') or not g.is_dachido_admin:
            if request.path.startswith('/api/'):
                from flask import jsonify
                return jsonify({"error": "Dachido admin access required"}), 403
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


def can_access_organization(user_org, target_org, user_role):
    """
    Check if user can access data for a specific organization
    - Dachido admins can access all organizations
    - Regular users can only access their own organization
    """
    if is_dachido_admin(user_org, user_role):
        return True
    return user_org.lower() == target_org.lower()


def has_permission(permission_name):
    """
    Check if user has a specific permission
    Can be extended with a permissions system
    """
    if not hasattr(g, 'role'):
        return False
    
    # Define permission mappings
    permissions = {
        'dachido_admin': ['*'],  # All permissions
        'admin': ['view_dashboard', 'manage_users', 'view_analytics', 'manage_recordings'],
        'customer_admin': ['view_dashboard', 'view_analytics', 'view_recordings']
    }
    
    user_permissions = permissions.get(g.role, [])
    return '*' in user_permissions or permission_name in user_permissions