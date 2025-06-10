from fastapi import APIRouter, HTTPException, Depends
from firebase_admin import auth
from auth import get_current_user
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from schema import UserProfile, UserRegistration
from firebase_config import get_firestore_db
from datetime import datetime

router = APIRouter(
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/v1/user/me")
async def get_current_user_profile(user = Depends(get_current_user)):
    """Get current user profile information"""
    try:
        # Get the user ID from the token
        uid = user["uid"]
        
        # Fetch the latest user data from Firebase
        user_record = auth.get_user(uid)
        
        # Return fresh user data
        return {
            "uid": user_record.uid,
            "email": user_record.email,
            "email_verified": user_record.email_verified,
            "display_name": user_record.display_name,
            "photo_url": user_record.photo_url,
            "disabled": user_record.disabled,
            "creation_timestamp": user_record.user_metadata.creation_timestamp,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile: {e}")

# Update user profile information
@router.put("/v1/user/profile")
async def update_user_profile(profile: UserProfile, user = Depends(get_current_user)):
    """Update user profile information"""
    try:
        # Update the user's profile in Firebase Authentication
        auth.update_user(
            user["uid"],
            display_name=profile.display_name,
            email=profile.email,
            # phone_number=profile.phone_number,
        )
        
        # Also update in Firestore
        db = get_firestore_db()
        user_doc_id = f"user_{user['uid']}"
        
        # Update the Firestore document
        db.collection("User").document(user_doc_id).update({
            "name": profile.display_name,
            "email": profile.email,
            "updatedAt": datetime.utcnow()
        })
        
        return {"message": "Profile updated successfully in both Auth and Firestore"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {e}")

# Register a new user 
@router.post("/v1/auth/register")
async def register_user(user_data: UserRegistration):
    """Register a new user in Firebase Authentication and Firestore"""
    try:
        # Create the user in Firebase Auth
        user_record = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.display_name
        )
        
        # Get Firestore DB
        db = get_firestore_db()
        
        # Create document ID with user_ prefix
        user_doc_id = f"user_{user_record.uid}"
        
        # Create user document in Firestore
        user_doc = {
            "userId": user_doc_id,
            "name": user_data.display_name,
            "group": user_data.group,
            "createdAt": datetime.utcnow()
        }
        
        # Add to "User" collection with user_{uid} as document ID
        db.collection("User").document(user_doc_id).set(user_doc)
        
        return {
            "message": "User created successfully",
            "uid": user_record.uid,
            "email": user_record.email,
            "display_name": user_data.display_name,
            "group": user_data.group
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating user: {str(e)}")