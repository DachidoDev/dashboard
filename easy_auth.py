"""
Azure App Service Easy Auth Integration Module
Handles authentication via Azure Easy Auth while maintaining custom JWT tokens
with organization and role information.
"""

import os
import json
from flask import request

# Easy Auth headers that Azure injects
EASY_AUTH_HEADERS = {
    'user_id': 'X-MS-CLIENT-PRINCIPAL-ID',
    'user_name': 'X-MS-CLIENT-PRINCIPAL-NAME',
    'provider': 'X-MS-CLIENT-PRINCIPAL-IDP',
    'claims': 'X-MS-CLIENT-PRINCIPAL',
    'name': 'X-MS-CLIENT-PRINCIPAL-NAME',
    'email': 'X-MS-CLIENT-PRINCIPAL-NAME',  # Often email for Microsoft Entra
}

# Check if Easy Auth is enabled
def is_easy_auth_enabled():
    """Check if Easy Auth is enabled by looking for Easy Auth headers"""
    return bool(request.headers.get(EASY_AUTH_HEADERS['user_id']))


def get_easy_auth_user():
    """
    Extract user information from Easy Auth headers
    Returns (user_id, user_name, provider, email) or (None, None, None, None)
    """
    if not is_easy_auth_enabled():
        return None, None, None, None
    
    user_id = request.headers.get(EASY_AUTH_HEADERS['user_id'])
    user_name = request.headers.get(EASY_AUTH_HEADERS['user_name'])
    provider = request.headers.get(EASY_AUTH_HEADERS['provider'], 'unknown')
    
    # Try to extract email from user_name (common for Microsoft Entra)
    email = user_name if '@' in str(user_name) else None
    
    return user_id, user_name, provider, email


def get_easy_auth_claims():
    """
    Parse Easy Auth claims from X-MS-CLIENT-PRINCIPAL header
    Returns dict of claims or None
    """
    claims_header = request.headers.get(EASY_AUTH_HEADERS['claims'])
    if not claims_header:
        return None
    
    try:
        import base64
        claims_json = base64.b64decode(claims_header).decode('utf-8')
        claims = json.loads(claims_json)
        return claims
    except Exception as e:
        print(f"⚠️  Error parsing Easy Auth claims: {e}")
        return None


def map_easy_auth_to_organization(easy_auth_user_id, easy_auth_email=None):
    """
    Map Easy Auth user identity to organization and role
    Uses user_mappings.json to store mappings
    
    Returns (organization, role, username) or (None, None, None)
    """
    # Import here to avoid circular import
    from auth import load_users
    
    MAPPINGS_FILE = "user_mappings.json"
    if os.environ.get("WEBSITE_INSTANCE_ID"):  # Running on Azure
        MAPPINGS_FILE = "/home/site/data/user_mappings.json"
    
    # Ensure directory exists
    mappings_dir = os.path.dirname(MAPPINGS_FILE)
    if mappings_dir and not os.path.exists(mappings_dir):
        os.makedirs(mappings_dir, exist_ok=True)
    
    # Load mappings
    if os.path.exists(MAPPINGS_FILE):
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
    else:
        mappings = {}
    
    # Look up user by Easy Auth ID or email
    user_id_key = f"easy_auth_id:{easy_auth_user_id}"
    email_key = f"email:{easy_auth_email}" if easy_auth_email else None
    
    mapping = None
    if user_id_key in mappings:
        mapping = mappings[user_id_key]
    elif email_key and email_key in mappings:
        mapping = mappings[email_key]
    else:
        # Try to find by email in existing users.json
        users = load_users()
        if easy_auth_email:
            for user_key, user_data in users.items():
                if isinstance(user_data, dict):
                    user_email = user_data.get('email')
                    if user_email == easy_auth_email:
                        # Extract org and username from user_key (format: "org:username")
                        parts = user_key.split(':')
                        if len(parts) == 2:
                            org, username = parts
                            role = user_data.get('role', 'customer_admin')
                            # Create mapping
                            mapping = {
                                'organization': org,
                                'role': role,
                                'username': username,
                                'easy_auth_id': easy_auth_user_id,
                                'email': easy_auth_email
                            }
                            # Save mapping
                            mappings[user_id_key] = mapping
                            if email_key:
                                mappings[email_key] = mapping
                            with open(MAPPINGS_FILE, 'w') as f:
                                json.dump(mappings, f, indent=4)
                            break
    
    if mapping:
        return mapping.get('organization'), mapping.get('role'), mapping.get('username')
    
    return None, None, None


def create_user_mapping(easy_auth_user_id, easy_auth_email, organization, username, role):
    """
    Create a mapping between Easy Auth identity and organization/role
    """
    MAPPINGS_FILE = "user_mappings.json"
    if os.environ.get("WEBSITE_INSTANCE_ID"):  # Running on Azure
        MAPPINGS_FILE = "/home/site/data/user_mappings.json"
    
    # Ensure directory exists
    mappings_dir = os.path.dirname(MAPPINGS_FILE)
    if mappings_dir and not os.path.exists(mappings_dir):
        os.makedirs(mappings_dir, exist_ok=True)
    
    # Load mappings
    if os.path.exists(MAPPINGS_FILE):
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
    else:
        mappings = {}
    
    # Create mapping entries
    user_id_key = f"easy_auth_id:{easy_auth_user_id}"
    email_key = f"email:{easy_auth_email}" if easy_auth_email else None
    
    mapping = {
        'organization': organization,
        'role': role,
        'username': username,
        'easy_auth_id': easy_auth_user_id,
        'email': easy_auth_email
    }
    
    mappings[user_id_key] = mapping
    if email_key:
        mappings[email_key] = mapping
    
    # Save mappings
    with open(MAPPINGS_FILE, 'w') as f:
        json.dump(mappings, f, indent=4)
    
    return True


def get_user_from_easy_auth():
    """
    Get user information from Easy Auth and map to organization/role
    Returns (username, organization, role) or (None, None, None)
    """
    if not is_easy_auth_enabled():
        return None, None, None
    
    easy_auth_user_id, easy_auth_user_name, provider, email = get_easy_auth_user()
    
    if not easy_auth_user_id:
        return None, None, None
    
    # Map Easy Auth user to organization/role
    organization, role, username = map_easy_auth_to_organization(easy_auth_user_id, email or easy_auth_user_name)
    
    if organization and role:
        return username or easy_auth_user_name, organization, role
    
    # If no mapping exists, return None (user needs to be mapped first)
    return None, None, None


def generate_custom_jwt_from_easy_auth():
    """
    Generate custom JWT token from Easy Auth identity
    This allows us to add organization/role to the token
    """
    # Import here to avoid circular import
    from auth import generate_jwt_token
    
    username, organization, role = get_user_from_easy_auth()
    
    if not username or not organization:
        return None
    
    # Generate JWT token with organization and role
    token = generate_jwt_token(username, organization, role)
    return token

