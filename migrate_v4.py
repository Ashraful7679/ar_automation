import sqlite3
import os

db_path = r"e:\Completed Projects\AR_Automation\ar_system.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(file_history)")
    columns = [c[1] for c in cursor.fetchall()]
    
    if "user_id" not in columns:
        print("Adding 'user_id' column to 'file_history'...")
        cursor.execute("ALTER TABLE file_history ADD COLUMN user_id INTEGER")
    
    conn.commit()
    conn.close()
    print("Migration successful.")
except Exception as e:
    print(f"Migration error: {e}")
