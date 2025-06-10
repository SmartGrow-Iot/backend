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
    """Get current user profile information from Firebase Auth with Firestore data"""
    try:
        # Get the user ID from the token
        uid = user["uid"]
        
        # Fetch the latest user data from Firebase
        user_record = auth.get_user(uid)
        
        # Create the base response from Auth data
        response = {
            "uid": user_record.uid,
            "email": user_record.email,
            "email_verified": user_record.email_verified,
            "display_name": user_record.display_name,
            "photo_url": user_record.photo_url,
            "disabled": user_record.disabled,
            "creation_timestamp": user_record.user_metadata.creation_timestamp,
        }
        
        # Try to get additional data from Firestore
        try:
            db = get_firestore_db()
            user_doc_id = f"user_{uid}"
            doc = db.collection("User").document(user_doc_id).get()
            
            if doc.exists:
                firestore_data = doc.to_dict()
                if "group" in firestore_data:
                    response["group"] = firestore_data["group"]
        except Exception:
            # Silently continue if Firestore data retrieval fails
            pass
            
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile: {e}")
    
@router.get("/v1/user/profile")
async def get_user_profile_from_firestore(user = Depends(get_current_user)):
    """Get current user profile from Firestore database"""
    try:
        # Get the user ID from the token
        uid = user["uid"]
        
        # Construct the document ID with user_ prefix
        user_doc_id = f"user_{uid}"
        
        # Get Firestore DB
        db = get_firestore_db()
        
        # Fetch the user document from Firestore
        doc_ref = db.collection("User").document(user_doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="User profile not found in database")
        
        # Get the document data
        user_data = doc.to_dict()
        
        # Convert any timestamp objects to ISO format strings
        if "createdAt" in user_data and hasattr(user_data["createdAt"], "isoformat"):
            user_data["createdAt"] = user_data["createdAt"].isoformat() + "Z"
        
        if "updatedAt" in user_data and hasattr(user_data["updatedAt"], "isoformat"):
            user_data["updatedAt"] = user_data["updatedAt"].isoformat() + "Z"
        
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile from database: {e}")

# Update user profile information
@router.put("/v1/user/profile")
async def update_user_profile(profile: UserProfile, user = Depends(get_current_user)):
    """Update user profile information"""
    try:
        # Update the user's profile in Firebase Authentication
        update_args = {
            "display_name": profile.display_name,
        }
        
        if profile.email:
            update_args["email"] = profile.email
            
        auth.update_user(user["uid"], **update_args)
        
        # Also update in Firestore
        db = get_firestore_db()
        user_doc_id = f"user_{user['uid']}"
        
        # Prepare update data
        update_data = {
            "name": profile.display_name,
            "updatedAt": datetime.utcnow()
        }
        
        if profile.email:
            update_data["email"] = profile.email
            
        if profile.group is not None:
            update_data["group"] = profile.group
        
        # Update the Firestore document
        db.collection("User").document(user_doc_id).update(update_data)
        
        return {
            "message": "Profile updated successfully",
            "updated_fields": list(update_data.keys())
        }
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