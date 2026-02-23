
import os
import psycopg2
import sys

def check_db():
    url = os.environ.get("POSTGRES_URL")
    if not url:
        print("ERROR: POSTGRES_URL environment variable not set.")
        return

    print(f"Connecting to database... (URL length: {len(url)})")
    try:
        conn = psycopg2.connect(url)
        print("Connected successfully.")
        
        cursor = conn.cursor()
        
        # Check columns
        print("\nChecking columns in 'queries' table:")
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'queries';")
        columns = cursor.fetchall()
        
        found_ip = False
        for col in columns:
            print(f" - {col[0]} ({col[1]})")
            if col[0] == 'ip_address':
                found_ip = True
        
        if found_ip:
            print("\nSUCCESS: 'ip_address' column exists.")
        else:
            print("\nFAILURE: 'ip_address' column MISSING.")

        # Check recent rows
        print("\nCreating a test query from this script to check insertion...")
        try:
            cursor.execute("INSERT INTO queries (user_text, horizon, severity, model_used, response_preview, ip_address) VALUES (%s, %s, %s, %s, %s, %s)",
                           ("DEBUG_PROBE", "test", "test", "debug_script", "Checking DB", "127.0.0.99"))
            conn.commit()
            print("Inserted test row successfully.")
        except Exception as e:
            print(f"Failed to insert test row: {e}")
            conn.rollback()

        print("\nRecent 5 rows:")
        cursor.execute("SELECT id, left(user_text, 20), ip_address, created_at FROM queries ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(f" ID: {row[0]}, Text: {row[1]}..., IP: {row[2]}, Time: {row[3]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    check_db()
