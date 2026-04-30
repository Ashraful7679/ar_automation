import sqlite3
import os
from datetime import datetime

db_path = r"e:\Completed Projects\AR_Automation\ar_system.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(user)")
        columns = [c[1] for c in cursor.fetchall()]
        
        new_cols = [
            ("created_by_id", "INTEGER"),
            ("max_sub_users", "INTEGER DEFAULT 0"),
            ("total_quota", "INTEGER DEFAULT 1000"),
            ("used_quota", "INTEGER DEFAULT 0"),
            ("daily_quota", "INTEGER DEFAULT 50"),
            ("used_today", "INTEGER DEFAULT 0"),
            ("last_reset_date", "DATE")
        ]
        
        for col_name, col_type in new_cols:
            if col_name not in columns:
                print(f"Adding '{col_name}' column...")
                cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
        
        # Set default for last_reset_date if it was just added
        cursor.execute("UPDATE user SET last_reset_date = ? WHERE last_reset_date IS NULL", (datetime.now().date(),))
        
        conn.commit()
        conn.close()
        print("Migration v3 successful.")
    except Exception as e:
        print(f"Migration error: {e}")
