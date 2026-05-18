"""
Authentication Dependency using Supabase SDK
Allows FastAPI routes to securely verify users logged in via Google OAuth
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import logging

from config import settings

logger = logging.getLogger(__name__)

# Initialize the official Supabase client
# Safe-guarding in case keys are not configured
supabase_client: Client = None

if settings.supabase_url and settings.supabase_service_role_key:
    try:
        supabase_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        logger.info("✅ Supabase Auth Client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase Auth Client: {e}")

# Security scheme to extract Bearer token from header
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to verify a JWT access token using the official Supabase SDK.
    Injects the validated user dictionary into secure endpoints.
    """
    if not supabase_client:
        logger.error("Supabase Auth Client is uninitialized. Check environment variables.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is currently unavailable."
        )

    token = credentials.credentials

    try:
        # Call Supabase SDK to verify the JWT token
        response = supabase_client.auth.get_user(token)
        user = response.user

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token."
            )

        # Convert User object properties to standard dictionary format for easy route usage
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "app_metadata": user.app_metadata,
            "user_metadata": user.user_metadata,
            "created_at": user.created_at
        }

    except Exception as e:
        logger.warning(f"Failed JWT validation attempt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid."
        )
