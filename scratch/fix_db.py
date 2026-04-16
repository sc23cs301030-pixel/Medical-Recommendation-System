import sqlite3
import os

db_path = 'instance/healthcare.db'

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_admin' not in columns:
            print("Adding 'is_admin' column to 'user' table...")
            cursor.execute("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0")
            conn.commit()
            print("Column added successfully!")
        else:
            print("Column 'is_admin' already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
else:
    print(f"Database file not found at {db_path}")
