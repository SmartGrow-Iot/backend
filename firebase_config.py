# firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Get the base directory of the current file to resolve paths
BASE_DIR = Path(__file__).resolve().parent

# --- Configuration for Firebase Admin SDK ---
load_dotenv()
SERVICE_ACCOUNT_KEY_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")

# Firestore client instance
db = None

def initialize_firebase_admin():
    global db

    if not firebase_admin._apps:
        # Try JSON credentials first (for cloud deployment)
        if FIREBASE_CREDENTIALS_JSON:
            try:
                cred_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("Firebase Admin SDK initialized successfully with JSON credentials!")
                db = firestore.client()
                print("Firestore client initialized successfully!")
                return
            except Exception as e:
                print(f"Error initializing Firebase with JSON credentials: {e}")
        
        # Fallback to file path (for local development)
        if SERVICE_ACCOUNT_KEY_PATH:
            resolved_key_path = BASE_DIR / SERVICE_ACCOUNT_KEY_PATH
            print(f"Attempting to initialize Firebase with key from: {resolved_key_path}")

            if resolved_key_path.exists():
                try:
                    cred = credentials.Certificate(str(resolved_key_path))
                    firebase_admin.initialize_app(cred)
                    print("Firebase Admin SDK initialized successfully!")
                    db = firestore.client()
                    print("Firestore client initialized successfully!")
                    return
                except Exception as e:
                    print(f"Error initializing Firebase with service account: {e}")
            else:
                print(f"ERROR: Service account key file not found at: {resolved_key_path}")
        
        # Final fallback to default credentials
        print("Attempting to initialize with default credentials...")
        try:
            firebase_admin.initialize_app()
            print("Firebase Admin SDK initialized with default credentials.")
            db = firestore.client()
            print("Firestore client initialized successfully with default credentials!")
        except Exception as e:
            print(f"Error initializing Firebase with default credentials: {e}")
            raise RuntimeError("Failed to initialize Firebase Admin SDK")
    else:
        print("Firebase Admin SDK already initialized.")
        if db is None:
            db = firestore.client()

def get_firestore_db():
    """Returns the initialized Firestore client."""
    if db is None:
        raise RuntimeError("Firestore DB not initialized. Call initialize_firebase_admin() first.")
    return db