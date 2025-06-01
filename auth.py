from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from firebase_config import initialize_firebase_admin

# Initialize Firebase if not already done
initialize_firebase_admin()

# Create a reusable security scheme
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate Firebase ID token and return user information
    """
    try:
        # Verify the Firebase token
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        
        # Return the decoded token which contains user info
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )