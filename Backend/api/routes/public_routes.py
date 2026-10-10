"""
Public API Routes
Endpoints that do not require authentication
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from api.routes.lead_routes import LeadCreate, LeadResponse, get_repository, _format_lead_response
from api.rate_limit import rate_limit
from config import get_config
from services.database.repository import Repository

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================

router = APIRouter(
    prefix="/api/public",
    tags=["public"]
)

# ==================== ENDPOINTS ====================

@router.post(
    "/leads",
    response_model=LeadResponse,
    status_code=201,
    dependencies=[Depends(rate_limit(
        "public_leads",
        get_config().public_rate_limit_max,
        get_config().public_rate_limit_window_seconds,
    ))],
)
async def create_public_lead(
    lead_data: LeadCreate,
    repo: Repository = Depends(get_repository)
) -> Dict[str, Any]:
    """
    Create a new lead publicly (e.g. from the landing page form).
    Does not require authentication.
    """
    try:
        # Check if lead already exists
        existing = await repo.get_lead_by_phone(lead_data.phone)
        if existing:
            logger.warning(f"Public attempt to create duplicate lead: {lead_data.phone}")
            # Throw 409 Conflict if they already submitted
            raise HTTPException(status_code=409, detail="We already have a request from this phone number. We will contact you soon!")

        # Create lead
        lead = await repo.create_lead(
            phone=lead_data.phone,
            name=lead_data.name,
            email=lead_data.email,
            language=lead_data.language
        )
        
        logger.info(f"[PUBLIC] Successfully created lead: {lead['id']}")
        return _format_lead_response(lead)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[PUBLIC] Error creating lead: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit form")
