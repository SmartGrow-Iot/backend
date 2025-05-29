# firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path
from dotenv import load_dotenv

# Get the base directory of the current file to resolve paths
BASE_DIR = Path(__file__).resolve().parent

# --- Configuration for Firebase Admin SDK ---
load_dotenv()
SERVICE_ACCOUNT_KEY_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")


# Firestore client instance
db = None

def initialize_firebase_admin():
    global db

    if not firebase_admin._apps:
        if SERVICE_ACCOUNT_KEY_PATH:
            resolved_key_path = BASE_DIR / SERVICE_ACCOUNT_KEY_PATH
            print(f"Attempting to initialize Firebase with key from: {resolved_key_path}")

            if resolved_key_path.exists():
                try:
                    cred = credentials.Certificate(str(resolved_key_path))
                    firebase_admin.initialize_app(cred)
                    print("Firebase Admin SDK initialized successfully!")
                    db = firestore.client() # Initialize Firestore client
                    print("Firestore client initialized successfully!")
                except Exception as e:
                    print(f"Error initializing Firebase with service account: {e}")
            else:
                print(f"ERROR: Service account key file not found at: {resolved_key_path}")
                print("Attempting to initialize with default credentials (might work in Google Cloud environments).")
                try:
                    firebase_admin.initialize_app()
                    print("Firebase Admin SDK initialized with default credentials.")
                    db = firestore.client()
                    print("Firestore client initialized successfully with default credentials!")
                except Exception as e:
                    print(f"Error initializing Firebase with default credentials: {e}")
        else:
            print("FIREBASE_CREDENTIALS_PATH environment variable not set.")
            print("Attempting to initialize with default credentials (might work in Google Cloud environments).")
            try:
                firebase_admin.initialize_app()
                print("Firebase Admin SDK initialized with default credentials.")
                db = firestore.client()
                print("Firestore client initialized successfully with default credentials!")
            except Exception as e:
                print(f"Error initializing Firebase with default credentials: {e}")
    else:
        print("Firebase Admin SDK already initialized.")
        if db is None: # Ensure db is set if app was already initialized elsewhere
             db = firestore.client()

def get_firestore_db():
    """Returns the initialized Firestore client."""
    if db is None:
        raise RuntimeError("Firestore DB not initialized. Call initialize_firebase_admin() first.")
    return db