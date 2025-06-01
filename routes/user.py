from fastapi import APIRouter, HTTPException, Depends
from firebase_admin import auth
from auth import get_current_user
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from schema import UserProfile, UserRegistration

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
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {e}")

# Register a new user 
@router.post("/v1/auth/register")
async def register_user(user_data: UserRegistration):
    """Register a new user in Firebase Authentication"""
    try:
        # Create the user in Firebase Auth
        user_record = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.display_name
        )
        
        return {
            "message": "User created successfully",
            "uid": user_record.uid,
            "email": user_record.email,
            "display_name": user_record.display_name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating user: {str(e)}")