# JWT Token Implementation - How It Works

## Overview

The system uses **JWT (JSON Web Tokens)** for stateless authentication. JWT tokens are stored as **HTTP-only cookies** to prevent XSS attacks and automatically expire after **30 minutes**.

---

## 🔐 JWT Configuration

**Location**: `auth.py` (lines 22-25)

```python
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your_super_secret_jwt_key_change_in_production")
JWT_ALGORITHM = "HS256"  # HMAC SHA-256
JWT_EXPIRATION_MINUTES = 30
```

**Key Points**:
- Secret key should be set via environment variable `JWT_SECRET_KEY` in production
- Uses HS256 algorithm (symmetric encryption)
- Tokens expire after 30 minutes

---

## 📋 Token Payload Structure

When a JWT token is generated, it contains:

```json
{
  "username": "admin",
  "organization": "coromandel",
  "role": "customer_admin",
  "exp": 1234567890,  // Expiration timestamp (UTC)
  "iat": 1234567890   // Issued at timestamp (UTC)
}
```

**Fields**:
- `username`: User's login name
- `organization`: Organization the user belongs to
- `role`: User's role (`dachido_admin`, `admin`, or `customer_admin`)
- `exp`: Expiration time (30 minutes from creation)
- `iat`: Token creation time

---

## 🔄 Authentication Flow

### 1. **Login Process** (`/login` route)

**Location**: `app.py` (lines 1843-1874)

**Steps**:
1. User submits: `organization`, `username`, `password`
2. System calls `auth.check_password(organization, username, password)`
3. If valid, generates JWT token: `auth.generate_jwt_token(username, org, role)`
4. Sets token as HTTP-only cookie named `auth_token`
5. Redirects to dashboard

**Cookie Settings**:
```python
response.set_cookie(
    "auth_token",
    token,
    max_age=30 * 60,        # 30 minutes
    httponly=True,          # Not accessible via JavaScript (XSS protection)
    secure=True,            # HTTPS only in production
    samesite="Lax"          # CSRF protection
)
```

### 2. **Token Generation** (`generate_jwt_token`)

**Location**: `auth.py` (lines 145-164)

**Process**:
```python
def generate_jwt_token(username, organization, role):
    expiration = datetime.utcnow() + timedelta(minutes=30)
    
    payload = {
        "username": username,
        "organization": organization,
        "role": role,
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token  # Returns a string like: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Output**: A signed JWT token string that can be verified later

---

## 🛡️ Token Verification Flow

### 1. **Protected Routes** (`@login_required` decorator)

**Location**: `auth.py` (lines 202-222)

**How it works**:
```python
@login_required
def my_protected_route():
    # This code only runs if token is valid
    pass
```

**Process**:
1. Decorator calls `get_user_from_token()`
2. Extracts `auth_token` cookie from request
3. Verifies token using `verify_jwt_token()`
4. If valid, populates Flask's `g` object with user info
5. If invalid/expired, redirects to login page

### 2. **Token Extraction** (`get_user_from_token`)

**Location**: `auth.py` (lines 181-194)

**Process**:
```python
def get_user_from_token():
    token = request.cookies.get("auth_token")  # Get from cookie
    if not token:
        return None, None, None
    
    success, payload = verify_jwt_token(token)  # Verify signature & expiration
    if not success:
        return None, None, None
    
    return payload.get("username"), payload.get("organization"), payload.get("role")
```

### 3. **Token Verification** (`verify_jwt_token`)

**Location**: `auth.py` (lines 167-178)

**Process**:
```python
def verify_jwt_token(token):
    try:
        # Decode and verify token signature
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, {"error": "Token expired"}  # Token is too old
    except jwt.InvalidTokenError:
        return False, {"error": "Invalid token"}   # Token is corrupted/fake
```

**What it checks**:
- ✅ Token signature is valid (not tampered with)
- ✅ Token hasn't expired (`exp` claim)
- ✅ Token format is correct

---

## 🎯 User Context in Requests

After successful token verification, user info is stored in Flask's `g` object:

**Location**: `auth.py` (lines 214-218)

```python
g.username = username           # e.g., "admin"
g.organization = organization   # e.g., "coromandel"
g.role = role                   # e.g., "customer_admin"
g.is_dachido_admin = is_dachido_admin(organization, role)  # True/False
```

**Usage in routes**:
```python
@app.route("/api/data")
@login_required
def get_data():
    org = g.organization  # Access user's organization
    role = g.role          # Access user's role
    # ... filter data by organization
```

---

## 🚪 Logout Process

**Location**: `app.py` (lines 1903-1908)

**Process**:
```python
@app.route("/logout")
def logout():
    response = make_response(redirect(url_for("login")))
    response.set_cookie("auth_token", "", expires=0)  # Delete cookie
    return response
```

**What happens**:
- Cookie is deleted by setting it to empty string with `expires=0`
- User is redirected to login page
- Next request will have no token, so `@login_required` will redirect to login

---

## 🔒 Security Features

### 1. **HTTP-Only Cookies**
- Cookie cannot be accessed via JavaScript
- Prevents XSS (Cross-Site Scripting) attacks
- Only sent to server automatically

### 2. **Secure Flag (Production)**
- Cookie only sent over HTTPS in production
- Prevents man-in-the-middle attacks

### 3. **SameSite=Lax**
- Prevents CSRF (Cross-Site Request Forgery) attacks
- Cookie only sent for same-site requests

### 4. **Token Expiration**
- Tokens expire after 30 minutes
- Forces re-authentication periodically
- Reduces risk if token is stolen

### 5. **Signed Tokens**
- Tokens are cryptographically signed with secret key
- Cannot be tampered with without secret key
- Server can verify token authenticity

---

## 📊 Token Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    JWT Token Lifecycle                        │
└─────────────────────────────────────────────────────────────┘

1. USER LOGS IN
   ├─> Submit: organization + username + password
   ├─> Verify credentials
   └─> Generate JWT token (30 min expiration)

2. TOKEN STORED
   └─> Set as HTTP-only cookie: "auth_token"

3. SUBSEQUENT REQUESTS
   ├─> Browser sends cookie automatically
   ├─> Server extracts token from cookie
   ├─> Verify token signature & expiration
   └─> Populate g.username, g.organization, g.role

4. TOKEN EXPIRES (after 30 minutes)
   ├─> verify_jwt_token() returns False
   ├─> @login_required redirects to /login
   └─> User must log in again

5. USER LOGS OUT
   ├─> Delete cookie (set expires=0)
   └─> Redirect to login
```

---

## 🔍 Example Token

**Generated Token** (simplified):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwi
b3JnYW5pemF0aW9uIjoiY29yb21hbmRlbCIsInJvbGUiOiJjdXN0b21lcl9hZG1p
biIsImV4cCI6MTcwMzQ1Njc4MCwiaWF0IjoxNzAzNDU0OTgwfQ.signature
```

**Decoded Payload**:
```json
{
  "username": "admin",
  "organization": "coromandel",
  "role": "customer_admin",
  "exp": 1703456780,
  "iat": 1703454980
}
```

---

## ⚙️ Configuration for Production

**Environment Variables** (set in Azure App Settings):

```bash
JWT_SECRET_KEY=<strong-random-secret-key>  # Must be strong and secret!
FLASK_ENV=production                        # Enables secure cookies
```

**Important**: 
- Use a **strong, random secret key** (at least 32 characters)
- Never commit `JWT_SECRET_KEY` to Git
- Rotate secret key periodically for security
- In Azure, set via App Settings → Configuration

---

## 🐛 Troubleshooting

### Token Expired
- **Symptom**: User redirected to login after 30 minutes
- **Solution**: Normal behavior, user must log in again

### Invalid Token
- **Symptom**: User redirected to login immediately
- **Causes**: 
  - Token was tampered with
  - Secret key changed
  - Token format corrupted
- **Solution**: User must log in again

### Cookie Not Set
- **Symptom**: User can't stay logged in
- **Causes**:
  - Browser blocks cookies
  - HTTPS required but using HTTP
- **Solution**: Check browser settings, ensure HTTPS in production

---

## 📝 Summary

**JWT Token Flow**:
1. ✅ User logs in → Token generated with user info
2. ✅ Token stored as HTTP-only cookie (30 min expiration)
3. ✅ Every request → Token extracted from cookie
4. ✅ Token verified → User info available via `g` object
5. ✅ Token expires → User redirected to login

**Security**:
- ✅ HTTP-only cookies (XSS protection)
- ✅ Secure flag in production (HTTPS only)
- ✅ Signed tokens (tamper-proof)
- ✅ 30-minute expiration (limits exposure)
- ✅ SameSite=Lax (CSRF protection)

