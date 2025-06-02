"""
Test script to create a user in Firebase Authentication using the Firebase Admin SDK.
This script is intended for testing purposes only and should not be used in production.
To run this script, ensure you have the Firebase Admin SDK installed and a valid service account key JSON file.
Use the following command to run the script:
  python test_register_user.py
"""

import firebase_admin
from firebase_admin import credentials, auth
import json
import os

# Initialize Firebase
cred_path = os.getenv('FIREBASE_CREDENTIAL_PATH')
if not cred_path or not os.path.exists(cred_path):
    raise FileNotFoundError("Firebase credential file not found. Set the FIREBASE_CREDENTIAL_PATH environment variable.")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)


def create_user(email, password, display_name=None):
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=True
        )
        print(f"User created successfully: {user.uid}")
        return user
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

# Create a test user (change the credentials as needed here)
user = create_user(
    email="test1@example.com",
    password="Google123$",
    display_name="Test User1"
)

if user:
    # Get a custom token for this user (for testing)
    custom_token = auth.create_custom_token(user.uid)
    print(f"Custom token: {custom_token.decode('utf-8')}")