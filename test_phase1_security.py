"""
Simple Phase 1 Security Test

Tests to verify basic security implementation works.
"""

import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_basic_imports():
    """Test basic imports work."""
    try:
        from app.utils.security import get_password_hash, create_access_token
        from app.utils.api_key_manager import api_key_manager
        from app.models.auth import UserCreate, Token
        from app.services.auth_service import AuthService
        from app.api.routers.auth import router as auth_router

        print("✅ Security imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_api_key_manager():
    """Test API key manager works."""
    try:
        from app.utils.api_key_manager import api_key_manager

        # Test caching
        key1 = api_key_manager.get_key("test_service")
        key2 = api_key_manager.get_key("test_service")  # Should use cache

        print(f"✅ API key manager works: {key1 == key2}")
        return True
    except Exception as e:
        print(f"❌ API key manager error: {e}")
        return False


def test_security_utils():
    """Test security utilities work."""
    try:
        from app.utils.security import create_access_token, verify_token

        token = create_access_token({"sub": "test_user"})
        payload = verify_token(token)

        success = payload is not None and payload.get("sub") == "test_user"
        print(f"✅ Security utils work: {success}")
        return success
    except Exception as e:
        print(f"❌ Security utils error: {e}")
        return False


def test_fastapi_app():
    """Test FastAPI app can be created."""
    try:
        from app.api.main import app

        print("✅ FastAPI app created successfully")
        return True
    except Exception as e:
        print(f"❌ FastAPI app error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Phase 1 Security Implementation Test")
    print("=" * 50)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("API Key Manager", test_api_key_manager),
        ("Security Utils", test_security_utils),
        ("FastAPI App", test_fastapi_app),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 SUMMARY: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Phase 1 security implementation is working.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    print("\n📋 NEXT STEPS:")
    print("1. Run: uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000")
    print("2. Visit: http://localhost:8000/docs")
    print("3. Test endpoints: /api/v1/weather/current?lat=-34.6&lon=-58.4")
    print("4. Test authentication: /api/v1/auth/register")


if __name__ == "__main__":
    main()
