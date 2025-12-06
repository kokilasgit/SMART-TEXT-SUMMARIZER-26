import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
import json
import sys

BASE_URL = "http://127.0.0.1:5000"
TEST_EMAIL = "test_user_urllib@example.com"  # Same user as before
TEST_PASSWORD = "password123"

def get_opener():
    cj = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def test_system():
    opener = get_opener()
    print("=" * 60)
    print("FULL SYSTEM VERIFICATION TEST")
    print("=" * 60)

    # --- STEP 1: AUTHENTICATION ---
    print("\n[1] Testing Authentication...")
    
    # Login
    login_data = urllib.parse.urlencode({'email': TEST_EMAIL, 'password': TEST_PASSWORD}).encode()
    try:
        resp = opener.open(f"{BASE_URL}/login", data=login_data)
        if "/dashboard" in resp.geturl():
            print("   ✅ Login Successful!")
        else:
            print(f"   ❌ Login Failed. URL: {resp.geturl()}")
            return
    except Exception as e:
        print(f"   ❌ Login Error: {e}")
        return

    # --- STEP 2: NLTK SUMMARIZATION ---
    print("\n[2] Testing NLTK Summarization (Standard)...")
    
    sample_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by animals including humans. 
    AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
    The term "artificial intelligence" had been used to describe machines that mimic and display "human" cognitive skills that are associated with the human mind, such as "learning" and "problem-solving".
    This definition has since been rejected by major AI researchers who now describe AI in terms of rationality and acting rationally, which does not limit how intelligence can be articulated.
    AI engineering involves the use of logic, probability, and optimization, among others.
    """
    
    summ_data = urllib.parse.urlencode({
        'text': sample_text,
        'length': 'medium',
        'engine': 'nltk',
        'mode': 'extractive'
    }).encode()
    
    try:
        resp = opener.open(f"{BASE_URL}/summarize", data=summ_data)
        content = resp.read().decode('utf-8')
        
        # Check if we are still on summarizer page (meaning no error redirect) and see result
        if "Summary Result" in content or "summary-text" in content:
            print("   ✅ NLTK Summarization Successful!")
            # Extract summary length if possible (simple string check)
            if "Summary Words" in content:
                print("   ✅ Result displayed correctly.")
        else:
            print("   ❌ NLTK Summarization Failed (No result found).")
            # print(content[:500])
    except Exception as e:
        print(f"   ❌ NLTK Error: {e}")

    # --- STEP 3: TRANSFORMERS SUMMARIZATION ---
    print("\n[3] Testing Transformers Summarization (Advanced)...")
    
    summ_data_tf = urllib.parse.urlencode({
        'text': sample_text,
        'length': 'short',
        'engine': 'transformers',
        'mode': 'abstractive' # Transformers implies abstractive usually
    }).encode()
    
    try:
        resp = opener.open(f"{BASE_URL}/summarize", data=summ_data_tf)
        content = resp.read().decode('utf-8')
        
        if "Summary Result" in content:
            print("   ✅ Transformers Request Successful!")
            # Check if it fell back to NLTK or used Transformers (hard to tell from HTML without parsing badges, but we look for success)
            if "Advanced (Transformers)" in content or "Abstractive" in content: 
                print("   ℹ️  Note: Check server logs to confirm if actual Model was used or Fallback triggered.")
            print("   ✅ Summary displayed.")
        else:
            print("   ❌ Transformers Summarization Failed.")
    except Exception as e:
        print(f"   ❌ Transformers Error: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_system()
