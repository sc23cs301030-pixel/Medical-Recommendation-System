import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

# Configuration
SERVICE_ACCOUNT_KEY = 'serviceAccountKey.json'
SQLITE_DB_PATH = 'instance/healthcare.db'

if not os.path.exists(SERVICE_ACCOUNT_KEY):
    print(f"Error: {SERVICE_ACCOUNT_KEY} not found. Please place it in the root directory.")
    exit(1)

if not os.path.exists(SQLITE_DB_PATH):
    print(f"Error: {SQLITE_DB_PATH} not found.")
    exit(1)

# Initialize Firebase
cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
firebase_admin.initialize_app(cred)
db = firestore.client()

def migrate():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- Starting Migration (Username as ID) ---")

    # 0. Clear existing Firestore data if requested
    print("Clearing existing Firestore collections...")
    for collection_name in ['users', 'predictions']:
        docs = db.collection(collection_name).stream()
        for doc in docs:
            doc.reference.delete()
    print("Done clearing.")

    # 1. Migrate Users
    print("\nMigrating Users...")
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    
    user_id_map = {} # {old_sqlite_id: new_firestore_id}
    
    for user in users:
        username = user['username']
        user_data = {
            'username': username,
            'email': user['email'],
            'password': user['password'], # Note: These will still be hashes from SQLite
            'is_admin': bool(user['is_admin'])
        }
        # Use username as the document ID
        db.collection('users').document(username).set(user_data)
        user_id_map[user['id']] = username
        print(f"  Migrated user: {username}")

    # 2. Migrate Predictions
    print("\nMigrating Predictions...")
    cursor.execute("SELECT * FROM prediction")
    predictions = cursor.fetchall()
    
    for pred in predictions:
        old_user_id = pred['user_id']
        new_user_id = user_id_map.get(old_user_id)
        
        if not new_user_id:
            print(f"  Warning: Skipping prediction {pred['id']} because user {old_user_id} was not found.")
            continue
            
        # Parse timestamp
        ts_str = pred['timestamp']
        try:
            ts = datetime.strptime(ts_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except:
            ts = datetime.utcnow()

        prediction_data = {
            'user_id': new_user_id,
            'symptoms': pred['symptoms'],
            'predicted_disease': pred['predicted_disease'],
            'description': pred['description'],
            'timestamp': ts
        }
        # Use a readable ID for predictions: Username_Timestamp
        # Since multiple predictions might have same second in migration, we add an index
        doc_id = f"{new_user_id}_{ts.strftime('%Y%m%d_%H%M%S')}_{pred['id']}"
        db.collection('predictions').document(doc_id).set(prediction_data)
        print(f"  Migrated prediction for user {new_user_id}")

    conn.close()
    print("\n--- Migration Completed Successfully! ---")

if __name__ == '__main__':
    migrate()
