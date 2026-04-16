import sqlite3
import pandas as pd
import os

db_path = 'instance/healthcare.db'
users_excel = 'instance/users.xlsx'
preds_excel = 'instance/predictions.xlsx'

if not os.path.exists('instance'):
    os.makedirs('instance')

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        
        # Migrate Users
        print("Migrating Users...")
        users_df = pd.read_sql_query("SELECT * FROM user", conn)
        users_df.to_excel(users_excel, index=False)
        print(f"Users migrated to {users_excel}")
        
        # Migrate Predictions
        print("Migrating Predictions...")
        preds_df = pd.read_sql_query("SELECT * FROM prediction", conn)
        preds_df.to_excel(preds_excel, index=False)
        print(f"Predictions migrated to {preds_excel}")
        
        conn.close()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration error: {e}")
else:
    print("No database found to migrate.")
