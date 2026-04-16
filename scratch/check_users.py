import sqlite3
import os

db_path = 'instance/healthcare.db'

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, email, is_admin FROM user")
        users = cursor.fetchall()
        
        if not users:
            print("No users found in the database.")
        else:
            print("Current Users in Database:")
            print("-" * 50)
            for user in users:
                print(f"ID: {user[0]} | Username: {user[1]} | Email: {user[2]} | Admin: {'Yes' if user[3] else 'No'}")
            print("-" * 50)
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
else:
    print(f"Database file not found at {db_path}")
