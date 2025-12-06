import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhan@123",
        database="smart_summarizer"
    )

# ✅ TEST RUN BLOCK
if _name_ == "_main_":
    try:
        conn = get_db_connection()
        print("✅ Database Connected Successfully!")
        conn.close()
    except mysql.connector.Error as err:
        print("❌ Error:", err)
