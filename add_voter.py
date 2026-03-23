import os
import pymysql
from datetime import datetime
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

def add_voter():
    print("=== Add Eligible Voter to Database ===")
    email = input("Enter Voter Email: ").strip().lower()
    dob_str = input("Enter Date of Birth (YYYY-MM-DD): ").strip()

    try:
        # Validate exact format
        datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        print("❌ Error: Invalid date format. Must be YYYY-MM-DD.")
        return

    try:
        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DB", "voting_system")
        )
        cursor = conn.cursor()
        
        sql = "INSERT INTO registered_voters (email, date_of_birth) VALUES (%s, %s)"
        cursor.execute(sql, (email, dob_str))
        conn.commit()
        conn.close()
        
        print(f"\n✅ SUCCESS! {email} has been added to the eligible voter list.")
        
    except pymysql.err.IntegrityError:
        print(f"\n❌ Error: The email '{email}' is already registered!")
    except Exception as e:
        print(f"\n❌ Database error: {e}")

if __name__ == "__main__":
    add_voter()
