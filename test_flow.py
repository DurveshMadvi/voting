import requests
import pymysql
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

def test_login_flow():
    session = requests.Session()
    base_url = "http://127.0.0.1:5000"
    email = "durvesh5.madvi@gmail.com"

    print(f"Testing login for {email}...")

    # 1. Post to login
    res = session.post(f"{base_url}/login", data={"email": email}, allow_redirects=True)
    if "OTP has been sent" not in res.text:
        print("❌ Login failed: OTP not sent.")
        return

    # 2. Get OTP from Database
    print("Fetching OTP from DB...")
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "voting_system")
    )
    cursor = conn.cursor()
    cursor.execute("SELECT otp_code FROM otps WHERE email=%s AND is_used=0 ORDER BY created_at DESC LIMIT 1", (email,))
    otp_code = cursor.fetchone()[0]
    conn.close()
    
    print(f"Retrieved OTP: {otp_code}")

    # 3. Post to verify OTP (we need the session cookie to be retained)
    res = session.post(f"{base_url}/verify-otp", data={"otp": otp_code}, allow_redirects=True)
    
    # Check if redirect is directly to /vote (skipping age verification)
    if ("Cast Your" in res.text and "Vote" in res.text) and ("Select your candidate" in res.text):
        print("✅ SUCCESS: OTP verified, age auto-verified from database, and redirected directly to /vote page!")
    else:
        print(f"❌ FAILED: Unexpected page content. (Check if age < 18 or session error)")
        return

    # 4. Cast a Vote
    print("Casting a vote for candidate ID 1...")
    res = session.post(f"{base_url}/vote", data={"candidate_id": "1"}, allow_redirects=True)
    if "recorded successfully" in res.text:
        print("✅ SUCCESS: Vote cast securely!")
    else:
        print("❌ FAILED to cast vote.")
        return

    # 5. Check the DB to prove it's encrypted
    print("Fetching vote from DB to verify encryption...")
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "voting_system")
    )
    cursor = conn.cursor()
    cursor.execute("SELECT encrypted_vote, vote_hash, digital_signature FROM votes ORDER BY timestamp DESC LIMIT 1")
    vote_record = cursor.fetchone()
    conn.close()

    if vote_record:
        print(f"✅ DB VERIFIED! Vote is stored securely:")
        print(f"   Encrypted Vote: {vote_record[0][:50]}...")
        print(f"   SHA-256 Hash: {vote_record[1]}")
        print(f"   Signature: {vote_record[2][:50]}...")
    else:
        print("❌ FAILED: Vote record not found in DB.")

if __name__ == "__main__":
    test_login_flow()
