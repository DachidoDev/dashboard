# Testing Guide: Multi-Tenant Dashboard

## 🚀 Quick Start Testing

### 1. Start the Application

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Run the application
python app.py
```

The app will start on `http://127.0.0.1:5000`

### 2. Default Test Users

The application automatically creates these users on first run:

#### Dachido Admin (Super Admin)
- **Organization**: `dachido`
- **Username**: `admin`
- **Password**: `adminpass`
- **Role**: `dachido_admin`
- **Access**: Can see all organizations' data

#### Coromandel Admin (Sample Organization)
- **Organization**: `coromandel`
- **Username**: `admin`
- **Password**: `adminpass`
- **Role**: `admin`
- **Access**: Coromandel organization data only

#### Coromandel Customer (Sample Organization)
- **Organization**: `coromandel`
- **Username**: `customer`
- **Password**: `customer123`
- **Role**: `customer_admin`
- **Access**: Coromandel organization data only (limited view)

---

## 📋 Manual Testing Checklist

### Test 1: Login Flow

#### ✅ Test 1.1: Successful Login
1. Navigate to `http://127.0.0.1:5000`
2. You should be redirected to `/login`
3. Enter:
   - Organization: `coromandel`
   - Username: `customer`
   - Password: `customer123`
4. Click "Login"
5. **Expected**: Redirected to dashboard, JWT cookie set

#### ✅ Test 1.2: Invalid Credentials
1. Go to login page
2. Enter:
   - Organization: `coromandel`
   - Username: `wronguser`
   - Password: `wrongpass`
3. Click "Login"
4. **Expected**: Error message "Invalid Organization, Username, or Password"

#### ✅ Test 1.3: Missing Fields
1. Go to login page
2. Leave organization field empty
3. Click "Login"
4. **Expected**: Error message "Organization, username, and password are required"

#### ✅ Test 1.4: Dachido Admin Login
1. Login with:
   - Organization: `dachido`
   - Username: `admin`
   - Password: `adminpass`
2. **Expected**: Dashboard shows "Dachido" as organization name

---

### Test 2: Dashboard Display

#### ✅ Test 2.1: Organization Name Display
1. Login as Coromandel customer
2. **Expected**: 
   - Page title: "Coromandel - FieldForce Dashboard"
   - Header shows "Coromandel" (not hardcoded)
   - Logo icon shows "C"

#### ✅ Test 2.2: Dachido Dashboard
1. Login as Dachido admin
2. **Expected**:
   - Page title: "Dachido - FieldForce Dashboard"
   - Header shows "Dachido"
   - Logo icon shows "D"
   - Badge shows "DACHIDO ADMIN"

#### ✅ Test 2.3: User Info Display
1. Login with any user
2. **Expected**: 
   - Username displayed in header
   - Role badge visible (ADMIN, CUSTOMER, or DACHIDO ADMIN)
   - Logout button visible

---

### Test 3: JWT Token Functionality

#### ✅ Test 3.1: Token Expiration (30 minutes)
1. Login successfully
2. Wait 30 minutes (or manually expire token)
3. Try to access any protected route
4. **Expected**: Redirected to login page

#### ✅ Test 3.2: Cookie Properties
1. Login successfully
2. Open browser DevTools → Application → Cookies
3. Check `auth_token` cookie
4. **Expected**:
   - HttpOnly: ✅ (checked)
   - Secure: ✅ (in production)
   - SameSite: Lax
   - Expires: ~30 minutes from now

#### ✅ Test 3.3: Logout
1. Login successfully
2. Click "Logout"
3. **Expected**: 
   - Redirected to login
   - `auth_token` cookie removed
   - Cannot access protected routes

---

### Test 4: Organization Isolation

#### ✅ Test 4.1: Audio Recordings Filtering
1. Login as Coromandel customer
2. Navigate to AUDIO MONITOR / LIBRARY
3. Check pending/processed recordings
4. **Expected**: Only shows recordings with `coromandel/` prefix

#### ✅ Test 4.2: Dachido Admin Sees All
1. Login as Dachido admin
2. Navigate to AUDIO MONITOR
3. **Expected**: Can see recordings from all organizations (no prefix filter)

#### ✅ Test 4.3: Cross-Organization Access Prevention
1. Login as Coromandel customer
2. Try to access another organization's data
3. **Expected**: Only sees Coromandel data (organization context from JWT)

---

### Test 5: API Endpoints

#### ✅ Test 5.1: Protected Endpoints
1. Without logging in, try to access:
   - `http://127.0.0.1:5000/api/home/kpis`
2. **Expected**: Redirected to login

#### ✅ Test 5.2: Authenticated Access
1. Login as Coromandel customer
2. Open browser DevTools → Network tab
3. Navigate dashboard (triggers API calls)
4. **Expected**: 
   - All API calls return 200 OK
   - Data filtered by organization

#### ✅ Test 5.3: Organization Context in APIs
1. Login as Coromandel customer
2. Check API response headers/cookies
3. **Expected**: JWT token present in cookie, organization context used

---

### Test 6: User Management

#### ✅ Test 6.1: Create New Organization
```python
# In Python console or script
import auth
auth.add_organization("testorg", display_name="Test Organization")
```

1. Verify `organizations.json` created/updated
2. **Expected**: Organization added with metadata

#### ✅ Test 6.2: Create New User
```python
auth.add_user("testorg", "testuser", "testpass123", role="customer_admin")
```

1. Try to login with new user
2. **Expected**: Login successful, sees Test Organization dashboard

#### ✅ Test 6.3: User Already Exists
```python
# Try to add same user again
result = auth.add_user("testorg", "testuser", "newpass", role="admin")
# result should be False
```
1. **Expected**: Returns False, user not duplicated

---

## 🔍 Browser Testing Tools

### Chrome DevTools

1. **Application Tab**:
   - Check Cookies → `auth_token`
   - Verify cookie properties

2. **Network Tab**:
   - Monitor API requests
   - Check request headers
   - Verify responses

3. **Console Tab**:
   - Check for JavaScript errors
   - Verify JWT token in cookies

### Test JWT Token Manually

```javascript
// In browser console
document.cookie
// Should show: auth_token=eyJ0eXAiOiJKV1QiLCJhbGc...

// Decode JWT (for testing only - use jwt.io)
// Copy token value and paste at https://jwt.io
// Should see: username, organization, role, exp, iat
```

---

## 🧪 Automated Testing (Optional)

### Simple Test Script

Create `test_auth.py`:

```python
import auth
import jwt
from datetime import datetime, timedelta

def test_organization_management():
    """Test organization CRUD"""
    # Add organization
    result = auth.add_organization("testorg", "Test Org")
    assert result == True
    
    # Get organization
    org = auth.get_organization("testorg")
    assert org is not None
    assert org["display_name"] == "Test Org"
    
    # Try to add again (should fail)
    result = auth.add_organization("testorg")
    assert result == False
    print("✅ Organization management works")

def test_user_management():
    """Test user CRUD"""
    # Add user
    result = auth.add_user("testorg", "testuser", "password123")
    assert result == True
    
    # Check password
    success, role, org = auth.check_password("testorg", "testuser", "password123")
    assert success == True
    assert role == "customer_admin"
    assert org == "testorg"
    
    # Wrong password
    success, _, _ = auth.check_password("testorg", "testuser", "wrongpass")
    assert success == False
    print("✅ User management works")

def test_jwt_token():
    """Test JWT token generation and verification"""
    # Generate token
    token = auth.generate_jwt_token("testuser", "testorg", "admin")
    assert token is not None
    assert isinstance(token, str)
    
    # Verify token
    success, payload = auth.verify_jwt_token(token)
    assert success == True
    assert payload["username"] == "testuser"
    assert payload["organization"] == "testorg"
    assert payload["role"] == "admin"
    
    # Check expiration
    exp = datetime.fromtimestamp(payload["exp"])
    now = datetime.utcnow()
    assert (exp - now).total_seconds() < 31 * 60  # Less than 31 minutes
    print("✅ JWT token works")

def test_dachido_admin():
    """Test Dachido admin check"""
    assert auth.is_dachido_admin("dachido", "dachido_admin") == True
    assert auth.is_dachido_admin("coromandel", "admin") == False
    assert auth.is_dachido_admin("dachido", "admin") == False
    print("✅ Dachido admin check works")

if __name__ == "__main__":
    print("Running authentication tests...")
    test_organization_management()
    test_user_management()
    test_jwt_token()
    test_dachido_admin()
    print("\n✅ All tests passed!")
```

Run with:
```bash
python test_auth.py
```

---

## 🐛 Common Issues & Troubleshooting

### Issue 1: "Invalid token" errors

**Symptoms**: Redirected to login immediately after login

**Possible Causes**:
1. JWT_SECRET_KEY changed between restarts
2. Token expired
3. Cookie not being set

**Solutions**:
- Check `JWT_SECRET_KEY` is consistent
- Clear cookies and login again
- Check browser console for cookie errors
- Verify cookie is set in DevTools → Application → Cookies

### Issue 2: Can't see audio recordings

**Symptoms**: Audio monitor shows empty or wrong recordings

**Possible Causes**:
1. Recordings not stored with organization prefix
2. Organization name mismatch (case-sensitive)

**Solutions**:
- Verify recordings in Azure Blob Storage have `{organization}/` prefix
- Check organization name matches exactly (lowercase)
- Dachido admins should see all recordings

### Issue 3: Organization name not displaying

**Symptoms**: Dashboard shows default or wrong organization name

**Possible Causes**:
1. Organization not created in `organizations.json`
2. Template variable not passed

**Solutions**:
- Check `organizations.json` exists and has organization
- Verify `organization_display_name` passed to template
- Check browser DevTools for template rendering

### Issue 4: Login redirects but no cookie

**Symptoms**: Login succeeds but immediately redirected back to login

**Possible Causes**:
1. Cookie not being set
2. Cookie blocked by browser
3. SameSite/secure settings

**Solutions**:
- Check browser DevTools → Application → Cookies
- Verify cookie settings in code
- Try different browser
- Check for HTTPS requirement in production

---

## 📊 Test Results Template

```
Date: ___________
Tester: ___________

[ ] Test 1.1: Successful Login - PASS/FAIL
[ ] Test 1.2: Invalid Credentials - PASS/FAIL
[ ] Test 1.3: Missing Fields - PASS/FAIL
[ ] Test 1.4: Dachido Admin Login - PASS/FAIL
[ ] Test 2.1: Organization Name Display - PASS/FAIL
[ ] Test 2.2: Dachido Dashboard - PASS/FAIL
[ ] Test 2.3: User Info Display - PASS/FAIL
[ ] Test 3.1: Token Expiration - PASS/FAIL
[ ] Test 3.2: Cookie Properties - PASS/FAIL
[ ] Test 3.3: Logout - PASS/FAIL
[ ] Test 4.1: Audio Recordings Filtering - PASS/FAIL
[ ] Test 4.2: Dachido Admin Sees All - PASS/FAIL
[ ] Test 4.3: Cross-Organization Access - PASS/FAIL
[ ] Test 5.1: Protected Endpoints - PASS/FAIL
[ ] Test 5.2: Authenticated Access - PASS/FAIL
[ ] Test 5.3: Organization Context - PASS/FAIL

Issues Found:
1. 
2. 
3. 

Notes:
```

---

## 🎯 Quick Smoke Test (5 minutes)

For a quick verification:

1. **Login Test**: Login with `coromandel` / `customer` / `customer123`
2. **Dashboard Check**: Verify "Coromandel" appears in header
3. **Logout Test**: Click logout, verify redirect to login
4. **Dachido Test**: Login with `dachido` / `admin` / `adminpass`, verify "Dachido" appears
5. **Cookie Check**: DevTools → Application → Cookies, verify `auth_token` exists

If all 5 pass, basic functionality is working! ✅

---

## 🔐 Security Testing

### Test Token Tampering
1. Login and get JWT token
2. Try to modify token in cookie
3. **Expected**: Request rejected, redirected to login

### Test Expired Token
1. Login and get token
2. Manually expire token (or wait 30 minutes)
3. Try to access protected route
4. **Expected**: Redirected to login

### Test Organization Bypass
1. Login as Organization A user
2. Try to access Organization B data via API
3. **Expected**: Only sees Organization A data (filtered by JWT)

---

## 📝 Next Steps After Testing

1. **Document Issues**: Note any bugs or unexpected behavior
2. **Performance Check**: Verify API response times
3. **Browser Compatibility**: Test in Chrome, Firefox, Safari
4. **Mobile Testing**: Test on mobile devices if needed
5. **Production Readiness**: Verify environment variables set correctly

---

**Happy Testing! 🚀**

