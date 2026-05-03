"""
RM (Relationship Manager) Management Routes

Endpoints:
- GET /api/rm/{rm_name}/queue - Get HOT leads assigned to RM
- POST /api/rm/assign - Assign a lead to RM
- POST /api/rm/{rm_name}/{lead_id}/complete - Mark lead as converted
- GET /api/rm/{rm_name}/dashboard - Get RM performance stats
- GET /api/rm/leaderboard - Get all RMs leaderboard
"""

import logging
from typing import Optional, Annotated
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from backend.services.database.repository import Repository
from backend.services.database.supabase_client import get_db_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rm", tags=["RM Management"])


# ==================== PYDANTIC MODELS ====================

class RMQueueLeadResponse(BaseModel):
    """Lead in RM's queue."""
    id: str
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    language: str
    status: str
    latest_score: Optional[float] = None
    assigned_at: str


class RMQueueResponse(BaseModel):
    """RM queue response."""
    rm_name: str
    total: int
    leads: list[RMQueueLeadResponse]


class RMAssignRequest(BaseModel):
    """Request to assign lead to RM."""
    lead_id: str = Field(..., description="UUID of lead to assign")
    rm_name: str = Field(..., description="Name of RM to assign to", min_length=1)


class RMAssignResponse(BaseModel):
    """Response after assigning lead."""
    success: bool
    lead_id: str
    rm_name: str
    assigned_at: str


class RMConvertRequest(BaseModel):
    """Request to mark lead as converted."""
    notes: Optional[str] = Field(None, description="Conversion notes")


class RMConvertResponse(BaseModel):
    """Response after marking converted."""
    success: bool
    lead_id: str
    rm_name: str
    converted_at: str


class RMStatsResponse(BaseModel):
    """RM performance statistics."""
    rm_name: str
    total_assigned: int
    converted: int
    pending: int
    conversion_rate: float


class RMLeaderboardEntry(BaseModel):
    """Single entry in RM leaderboard."""
    rank: int
    rm_name: str
    total_assigned: int
    converted: int
    conversion_rate: float


class RMLeaderboardResponse(BaseModel):
    """RM leaderboard response."""
    period: str
    total_rms: int
    entries: list[RMLeaderboardEntry]


# ==================== DEPENDENCY INJECTION ====================

async def get_repository() -> Repository:
    """Get repository instance."""
    db_client = await get_db_client()
    return Repository(db_client)


# ==================== ENDPOINTS ====================

@router.get("/{rm_name}/queue", response_model=RMQueueResponse)
async def get_rm_queue(
    rm_name: str = Path(..., description="Name of the RM"),
    repository: Repository = Depends(get_repository),
) -> dict:
    """
    Get all pending (not converted) HOT leads assigned to an RM.
    
    Args:
        rm_name: Name of the relationship manager
        
    Returns:
        RMQueueResponse with list of leads
    """
    try:
        leads = await repository.get_rm_queue(rm_name)
        
        formatted_leads = []
        for lead in leads:
            formatted_leads.append(
                RMQueueLeadResponse(
                    id=str(lead.get("id", "")),
                    phone=lead.get("phone", ""),
                    name=lead.get("name"),
                    email=lead.get("email"),
                    language=lead.get("language", "hi"),
                    status=lead.get("status", ""),
                    latest_score=lead.get("latest_score"),
                    assigned_at=lead.get("assigned_at", "").isoformat() if lead.get("assigned_at") else "",
                )
            )
        
        logger.info(f"Retrieved {len(leads)} pending leads for RM: {rm_name}")
        
        return {
            "rm_name": rm_name,
            "total": len(leads),
            "leads": formatted_leads,
        }
    except Exception as e:
        logger.error(f"Error getting RM queue for {rm_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assign", response_model=RMAssignResponse, status_code=201)
async def assign_lead_to_rm(
    request: RMAssignRequest,
    repository: Repository = Depends(get_repository),
) -> dict:
    """
    Assign a lead to a relationship manager.
    
    Typically used when a HOT lead is detected by the scoring engine,
    but can also be used for manual reassignments.
    
    Args:
        request: RMAssignRequest with lead_id and rm_name
        
    Returns:
        RMAssignResponse with assignment details
    """
    try:
        # Validate lead exists
        lead = await repository.get_lead(UUID(request.lead_id))
        if not lead:
            logger.warning(f"Lead not found: {request.lead_id}")
            raise HTTPException(status_code=404, detail=f"Lead {request.lead_id} not found")
        
        # Assign to RM
        assignment = await repository.assign_lead_to_rm(
            lead_id=UUID(request.lead_id),
            rm_name=request.rm_name,
        )
        
        logger.info(f"Assigned lead {request.lead_id} to RM {request.rm_name}")
        
        assigned_at = assignment.get("assigned_at", datetime.utcnow())
        if isinstance(assigned_at, str):
            assigned_at = datetime.fromisoformat(assigned_at)
        
        return {
            "success": True,
            "lead_id": str(assignment.get("lead_id", "")),
            "rm_name": request.rm_name,
            "assigned_at": assigned_at.isoformat(),
        }
    except ValueError as e:
        logger.error(f"Invalid lead_id format: {request.lead_id}")
        raise HTTPException(status_code=400, detail="Invalid lead_id format")
    except Exception as e:
        logger.error(f"Error assigning lead to RM: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{rm_name}/{lead_id}/complete", response_model=RMConvertResponse, status_code=200)
async def mark_lead_converted(
    rm_name: str = Path(..., description="Name of the RM"),
    lead_id: str = Path(..., description="UUID of the lead"),
    request: RMConvertRequest = None,
    repository: Repository = Depends(get_repository),
) -> dict:
    """
    Mark a lead as converted (sale completed).
    
    Updates the lead status to 'converted' and marks the RM assignment as complete.
    
    Args:
        rm_name: Name of the RM
        lead_id: UUID of the lead
        request: Optional conversion notes
        
    Returns:
        RMConvertResponse with conversion confirmation
    """
    try:
        # Validate lead exists
        lead = await repository.get_lead(UUID(lead_id))
        if not lead:
            logger.warning(f"Lead not found: {lead_id}")
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
        
        # Mark as converted
        success = await repository.mark_as_converted(UUID(lead_id))
        
        if not success:
            logger.warning(f"Failed to mark lead {lead_id} as converted")
            raise HTTPException(status_code=500, detail="Failed to update conversion status")
        
        logger.info(f"Lead {lead_id} marked as converted by RM {rm_name}")
        
        return {
            "success": True,
            "lead_id": lead_id,
            "rm_name": rm_name,
            "converted_at": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        logger.error(f"Invalid lead_id format: {lead_id}")
        raise HTTPException(status_code=400, detail="Invalid lead_id format")
    except Exception as e:
        logger.error(f"Error marking lead as converted: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rm_name}/dashboard", response_model=RMStatsResponse)
async def get_rm_dashboard(
    rm_name: str = Path(..., description="Name of the RM"),
    days: Annotated[int, Query(ge=1, le=365, description="Number of days to analyze")] = 30,
    repository: Repository = Depends(get_repository),
) -> dict:
    """
    Get performance dashboard for a specific RM.
    
    Shows conversion metrics, pending leads, and conversion rate for the specified period.
    
    Args:
        rm_name: Name of the RM
        days: Number of days to analyze (default 30, max 365)
        
    Returns:
        RMStatsResponse with performance metrics
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        stats = await repository.get_rm_stats(rm_name, start_date, end_date)
        
        if not stats:
            logger.info(f"No stats found for RM {rm_name}")
            stats = {
                "total_assigned": 0,
                "converted": 0,
                "pending": 0,
                "conversion_rate": 0.0,
            }
        
        logger.info(f"Retrieved dashboard stats for RM {rm_name}")
        
        return {
            "rm_name": rm_name,
            "total_assigned": stats.get("total_assigned", 0),
            "converted": stats.get("converted", 0),
            "pending": stats.get("pending", 0),
            "conversion_rate": stats.get("conversion_rate", 0.0),
        }
    except Exception as e:
        logger.error(f"Error getting RM dashboard for {rm_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard", response_model=RMLeaderboardResponse)
async def get_rm_leaderboard(
    days: Annotated[int, Query(ge=1, le=365, description="Number of days to analyze")] = 30,
    limit: Annotated[int, Query(ge=1, le=100, description="Max number of RMs")] = 10,
    repository: Repository = Depends(get_repository),
) -> dict:
    """
    Get RM leaderboard ranked by conversion rate.
    
    Shows top-performing relationship managers based on conversion metrics.
    
    Args:
        days: Number of days to analyze (default 30, max 365)
        limit: Maximum number of RMs to return (default 10, max 100)
        
    Returns:
        RMLeaderboardResponse with ranked list of RMs
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        leaderboard = await repository.get_rm_leaderboard(start_date, end_date, limit)
        
        entries = []
        for rank, entry in enumerate(leaderboard, 1):
            entries.append(
                RMLeaderboardEntry(
                    rank=rank,
                    rm_name=entry.get("rm_name", ""),
                    total_assigned=entry.get("total_assigned", 0),
                    converted=entry.get("converted", 0),
                    conversion_rate=entry.get("conversion_rate", 0.0),
                )
            )
        
        logger.info(f"Retrieved leaderboard with {len(entries)} entries")
        
        return {
            "period": f"Last {days} days",
            "total_rms": len(entries),
            "entries": entries,
        }
    except Exception as e:
        logger.error(f"Error getting RM leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
