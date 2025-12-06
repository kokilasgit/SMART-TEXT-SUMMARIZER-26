import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
import sys
import os

# Setup path to import app models
sys.path.append(os.getcwd())
from app import app, db, User

BASE_URL = "http://127.0.0.1:5000"
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASS = "admin123"
TARGET_EMAIL = "test_user_urllib@example.com"

def test_deactivate():
    print("-" * 50)
    print("Admin Deactivation Test")
    print("-" * 50)
    
    # 1. Get Target User ID
    user_id = None
    with app.app_context():
        target = User.query.filter_by(email=TARGET_EMAIL).first()
        if not target:
            print(f"❌ Target user {TARGET_EMAIL} not found. Run test_full_system.py first.")
            return
        user_id = target.id
        initial_status = target.is_active
        print(f"Target User ID: {user_id}")
        print(f"Initial Active Status: {initial_status}")

    # 2. Login as Admin
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    print("\n[1] Logging in as Admin...")
    login_data = urllib.parse.urlencode({'email': ADMIN_EMAIL, 'password': ADMIN_PASS}).encode()
    try:
        resp = opener.open(f"{BASE_URL}/admin/login", data=login_data)
        if "/admin/dashboard" in resp.geturl():
            print("   ✅ Admin Login Successful")
        else:
            print(f"   ❌ Admin Login Failed. URL: {resp.geturl()}")
            return
    except Exception as e:
        print(f"   ❌ Login Error: {e}")
        return

    # 3. Toggle User (Deactivate)
    print(f"\n[2] Toggling User {user_id}...")
    try:
        # POST request to toggle
        resp = opener.open(f"{BASE_URL}/admin/users/{user_id}/toggle", data=b"") # Empty POST data
        content = resp.read().decode('utf-8')
        
        if "/admin/users" in resp.geturl():
            print("   ✅ Toggle Request Sent (Redirected correctly)")
        else:
            print(f"   ❌ Toggle Request Failed. URL: {resp.geturl()}")
    except Exception as e:
        print(f"   ❌ Toggle Error: {e}")
        # Print error details if 400/500
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8')[:500])

    # 4. Verify DB Status
    with app.app_context():
        target = User.query.get(user_id)
        new_status = target.is_active
        print(f"\nNew Active Status: {new_status}")
        
        if new_status != initial_status:
            print("✅ User status changed successfully!")
        else:
            print("❌ User status DID NOT change.")

if __name__ == "__main__":
    test_deactivate()
