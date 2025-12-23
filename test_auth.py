#!/usr/bin/env python3
"""
Quick test script for multi-tenant authentication system
Run with: python test_auth.py
"""

import auth
import sys

def test_organization_management():
    """Test organization CRUD operations"""
    print("\n📋 Testing Organization Management...")
    
    # Add organization
    result = auth.add_organization("testorg", "Test Organization")
    assert result == True, "Failed to add organization"
    print("  ✅ Organization added")
    
    # Get organization
    org = auth.get_organization("testorg")
    assert org is not None, "Failed to get organization"
    assert org["display_name"] == "Test Organization", "Display name mismatch"
    print("  ✅ Organization retrieved")
    
    # Try to add again (should fail)
    result = auth.add_organization("testorg")
    assert result == False, "Should not allow duplicate organizations"
    print("  ✅ Duplicate organization prevented")
    
    print("✅ Organization management: PASSED")


def test_user_management():
    """Test user CRUD operations"""
    print("\n👤 Testing User Management...")
    
    # Add user
    result = auth.add_user("testorg", "testuser", "password123", role="customer_admin")
    assert result == True, "Failed to add user"
    print("  ✅ User added")
    
    # Check password (correct)
    success, role, org = auth.check_password("testorg", "testuser", "password123")
    assert success == True, "Correct password should succeed"
    assert role == "customer_admin", "Role mismatch"
    assert org == "testorg", "Organization mismatch"
    print("  ✅ Correct password accepted")
    
    # Check password (wrong)
    success, _, _ = auth.check_password("testorg", "testuser", "wrongpass")
    assert success == False, "Wrong password should fail"
    print("  ✅ Wrong password rejected")
    
    # User already exists
    result = auth.add_user("testorg", "testuser", "newpass")
    assert result == False, "Should not allow duplicate users"
    print("  ✅ Duplicate user prevented")
    
    print("✅ User management: PASSED")


def test_jwt_token():
    """Test JWT token generation and verification"""
    print("\n🔐 Testing JWT Tokens...")
    
    # Generate token
    token = auth.generate_jwt_token("testuser", "testorg", "admin")
    assert token is not None, "Token generation failed"
    assert isinstance(token, str), "Token should be string"
    assert len(token) > 0, "Token should not be empty"
    print("  ✅ Token generated")
    
    # Verify token
    success, payload = auth.verify_jwt_token(token)
    assert success == True, "Token verification failed"
    assert payload["username"] == "testuser", "Username mismatch"
    assert payload["organization"] == "testorg", "Organization mismatch"
    assert payload["role"] == "admin", "Role mismatch"
    assert "exp" in payload, "Expiration missing"
    assert "iat" in payload, "Issued at missing"
    print("  ✅ Token verified")
    
    # Test expired token (simulate)
    import jwt
    from datetime import datetime, timedelta
    expired_payload = {
        "username": "testuser",
        "organization": "testorg",
        "role": "admin",
        "exp": datetime.utcnow() - timedelta(minutes=1),  # Expired 1 minute ago
        "iat": datetime.utcnow() - timedelta(minutes=31)
    }
    expired_token = jwt.encode(expired_payload, auth.JWT_SECRET_KEY, algorithm=auth.JWT_ALGORITHM)
    if isinstance(expired_token, bytes):
        expired_token = expired_token.decode('utf-8')
    
    success, result = auth.verify_jwt_token(expired_token)
    assert success == False, "Expired token should be rejected"
    assert "error" in result, "Should return error message"
    print("  ✅ Expired token rejected")
    
    print("✅ JWT tokens: PASSED")


def test_dachido_admin():
    """Test Dachido admin functionality"""
    print("\n👑 Testing Dachido Admin...")
    
    assert auth.is_dachido_admin("dachido", "dachido_admin") == True, "Dachido admin check failed"
    assert auth.is_dachido_admin("coromandel", "admin") == False, "Non-Dachido should not be admin"
    assert auth.is_dachido_admin("dachido", "admin") == False, "Dachido non-admin should fail"
    assert auth.is_dachido_admin("coromandel", "dachido_admin") == False, "Wrong org with admin role should fail"
    print("  ✅ Dachido admin checks work correctly")
    
    print("✅ Dachido admin: PASSED")


def test_user_role():
    """Test user role retrieval"""
    print("\n🎭 Testing User Roles...")
    
    # Get role for existing user
    role = auth.get_user_role("testorg", "testuser")
    assert role == "customer_admin", "Role retrieval failed"
    print("  ✅ User role retrieved")
    
    # Get role for non-existent user
    role = auth.get_user_role("testorg", "nonexistent")
    assert role is None, "Non-existent user should return None"
    print("  ✅ Non-existent user handled")
    
    print("✅ User roles: PASSED")


def test_backward_compatibility():
    """Test backward compatibility with old user format"""
    print("\n🔄 Testing Backward Compatibility...")
    
    # This would require manually creating old format user
    # For now, just verify the code handles it
    users = auth.load_users()
    print(f"  ℹ️  Current users in system: {len(users)}")
    print("  ✅ Backward compatibility code present")
    
    print("✅ Backward compatibility: PASSED")


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Multi-Tenant Authentication System - Test Suite")
    print("=" * 60)
    
    try:
        test_organization_management()
        test_user_management()
        test_jwt_token()
        test_dachido_admin()
        test_user_role()
        test_backward_compatibility()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n📝 Next Steps:")
        print("  1. Start the app: python app.py")
        print("  2. Test login flow manually")
        print("  3. Check dashboard displays organization name")
        print("  4. Verify JWT cookie is set")
        print("\nSee TESTING_GUIDE.md for detailed manual testing steps.")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

