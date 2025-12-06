import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
import sys
import os

# Setup path
sys.path.append(os.getcwd())
from app import app, db, User

BASE_URL = "http://127.0.0.1:5000"
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASS = "admin123"
USER_EMAIL = "test_user_urllib@example.com"
USER_PASS = "password123" # Assuming this password from previous setup

def test_enforcement():
    print("-" * 50)
    print("Security Enforcement Test: Active Session vs Deactivation")
    print("-" * 50)

    # 1. Ensure User is initially ACTIVE
    user_id = None
    with app.app_context():
        u = User.query.filter_by(email=USER_EMAIL).first()
        if not u:
            print("❌ User not found.")
            return
        user_id = u.id
        u.is_active = True
        db.session.commit()
        print(f"User {u.email} (ID: {u.id}) set to ACTIVE.")

    # 2. Login USER (Create Session)
    cj_user = CookieJar()
    opener_user = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_user))
    
    print("\n[1] Logging in as User...")
    data = urllib.parse.urlencode({'email': USER_EMAIL, 'password': USER_PASS}).encode()
    try:
        resp = opener_user.open(f"{BASE_URL}/login", data=data)
        if "/dashboard" in resp.geturl():
            print("   ✅ User Login Successful")
        else:
            print(f"   ❌ User Login Failed. URL: {resp.geturl()}")
            return
    except Exception as e:
        print(f"   ❌ Login Error: {e}")
        return

    # 3. Login ADMIN (Separate Session)
    cj_admin = CookieJar()
    opener_admin = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_admin))
    print("\n[2] Logging in as Admin...")
    data_admin = urllib.parse.urlencode({'email': ADMIN_EMAIL, 'password': ADMIN_PASS}).encode()
    opener_admin.open(f"{BASE_URL}/admin/login", data=data_admin)
    print("   ✅ Admin Logged In")

    # 4. DEACTIVATE User via Admin
    print(f"\n[3] Deactivating User {user_id}...")
    opener_admin.open(f"{BASE_URL}/admin/users/{user_id}/toggle", data=b"")
    
    # Verify DB
    with app.app_context():
        u = User.query.get(user_id)
        print(f"   DB Status: is_active={u.is_active}")

    # 5. User Access Dashboard (Should be BLOCKED)
    print("\n[4] User accessing Dashboard...")
    try:
        resp = opener_user.open(f"{BASE_URL}/user/dashboard")
        final_url = resp.geturl()
        print(f"   Response URL: {final_url}")
        
        if "/login" in final_url:
            print("   ✅ BLOCKED. Redirected to Login.")
        elif "/dashboard" in final_url:
            print("   ❌ SECURITY HOLE: User still has access to Dashboard!")
        else:
            print(f"   ❓ Unknown state: {final_url}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_enforcement()
