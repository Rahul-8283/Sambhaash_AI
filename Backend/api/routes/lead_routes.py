"""
Lead Management API Routes
Handles CRUD operations for leads
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import csv
import json
import io
import logging

from services.database.supabase_client import get_db_client, SupabaseClient
from services.database.repository import Repository
from services.database.models import LeadStatus
from api.auth import get_current_user

logger = logging.getLogger(__name__)

# ==================== PYDANTIC MODELS ====================

class LeadCreate(BaseModel):
    """Request model for creating a lead"""
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number")
    name: Optional[str] = Field(None, max_length=255, description="Lead name")
    email: Optional[EmailStr] = Field(None, description="Email address")
    language: str = Field(default="hi", description="Preferred language")
    
    @validator('phone')
    def phone_must_be_valid(cls, v):
        """Validate phone format"""
        # Remove spaces and special chars except +
        clean_phone = v.replace(" ", "").replace("-", "")
        if not clean_phone.replace("+", "").isdigit():
            raise ValueError("Phone must contain only digits and optional +")
        if len(clean_phone) < 10:
            raise ValueError("Phone must be at least 10 digits")
        return clean_phone
    
    class Config:
        example = {
            "phone": "+919876543210",
            "name": "Rajesh Kumar",
            "email": "rajesh@example.com",
            "language": "hi"
        }


class LeadUpdate(BaseModel):
    """Request model for updating a lead"""
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = Field(None)
    language: Optional[str] = Field(None)
    status: Optional[str] = Field(None, description="new, contacted, interested, converted, rejected, follow_up")
    
    @validator('status')
    def status_must_be_valid(cls, v):
        """Validate status"""
        if v and v not in [s.value for s in LeadStatus]:
            raise ValueError(f"Status must be one of: {[s.value for s in LeadStatus]}")
        return v


class LeadResponse(BaseModel):
    """Response model for a lead"""
    id: str
    phone: str
    name: Optional[str]
    email: Optional[str]
    language: str
    status: str
    created_at: str
    updated_at: str
    currentScore: Optional[Dict[str, Any]] = None
    rmAssignment: Optional[Dict[str, Any]] = None
    
    class Config:
        example = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "phone": "+919876543210",
            "name": "Rajesh Kumar",
            "email": "rajesh@example.com",
            "language": "hi",
            "status": "NEW",
            "created_at": "2026-05-03T10:00:00",
            "updated_at": "2026-05-03T10:00:00"
        }


class LeadDetailResponse(LeadResponse):
    """Lead response with latest score and session info"""
    latest_score: Optional[Dict[str, Any]] = None
    last_call_session: Optional[Dict[str, Any]] = None
    total_calls: int = 0


class LeadListResponse(BaseModel):
    """Response model for list of leads"""
    total: int
    limit: int
    offset: int
    leads: List[LeadResponse]


class BatchUploadResponse(BaseModel):
    """Response model for batch upload"""
    created: int
    duplicates: int
    errors: int
    error_details: List[Dict[str, Any]] = []


class SearchResponse(BaseModel):
    """Response model for search results"""
    count: int
    results: List[LeadResponse]


# ==================== DEPENDENCY ====================

async def get_repository() -> Repository:
    """Get repository instance with database client"""
    db = await get_db_client()
    return Repository(db)


# ==================== ROUTER ====================

router = APIRouter(
    prefix="/api/leads",
    tags=["leads"],
    dependencies=[Depends(get_current_user)]
)


# ==================== ENDPOINTS ====================

@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(
    lead_data: LeadCreate,
    repo: Repository = Depends(get_repository)
) -> Dict[str, Any]:
    """
    Create a new lead.
    
    - **phone**: Unique phone number (required)
    - **name**: Lead name (optional)
    - **email**: Email address (optional)
    - **language**: Preferred language (default: hi)
    
    Returns: Created lead object
    """
    try:
        # Check if lead already exists
        existing = await repo.get_lead_by_phone(lead_data.phone)
        if existing:
            logger.warning(f"Attempt to create duplicate lead: {lead_data.phone}")
            raise HTTPException(
                status_code=409,
                detail=f"Lead with phone {lead_data.phone} already exists"
            )
        
        # Create lead
        lead = await repo.create_lead(
            phone=lead_data.phone,
            name=lead_data.name,
            email=lead_data.email,
            language=lead_data.language
        )
        
        logger.info(f"Created lead: {lead_data.phone}")
        return _format_lead_response(lead)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating lead: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating lead: {str(e)}"
        )


@router.get("", response_model=LeadListResponse)
async def list_leads(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: Repository = Depends(get_repository)
) -> Dict[str, Any]:
    """
    List all leads with optional filtering and pagination.
    
    - **status**: Filter by status (new, contacted, interested, converted, rejected, follow_up)
    - **limit**: Results per page (default: 50, max: 500)
    - **offset**: Pagination offset (default: 0)
    
    Returns: Paginated list of leads
    """
    try:
        if status:
            # Validate status
            valid_statuses = [s.value for s in LeadStatus]
            if status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {valid_statuses}"
                )
            leads, total = await repo.list_leads_by_status(status, limit, offset)
        else:
            leads, total = await repo.list_all_leads(limit, offset)
        
        logger.info(f"Listed {len(leads)} leads (total: {total})")
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "leads": [_format_lead_response(lead) for lead in leads]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing leads: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing leads: {str(e)}"
        )


@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(
    lead_id: str,
    repo: Repository = Depends(get_repository)
) -> Dict[str, Any]:
    """
    Get a single lead with latest score and call session.
    
    - **lead_id**: Lead UUID
    
    Returns: Lead object with scoring and session details
    """
    try:
        # Validate UUID format
        try:
            UUID(lead_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid lead ID format")
        
        lead = await repo.get_lead(UUID(lead_id))
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Get latest score
        latest_score = await repo.get_latest_score(UUID(lead_id))
        
        # Get last call session
        sessions = await repo.list_sessions_by_lead(UUID(lead_id), limit=1)
        last_session = sessions[0] if sessions else None
        
        # Count total calls
        all_sessions = await repo.list_sessions_by_lead(UUID(lead_id), limit=1000)
        total_calls = len(all_sessions)
        
        result = _format_lead_response(lead)
        result["latest_score"] = _format_dict(latest_score) if latest_score else None
        result["last_call_session"] = _format_dict(last_session) if last_session else None
        result["total_calls"] = total_calls
        
        logger.info(f"Retrieved lead: {lead_id}")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lead: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving lead: {str(e)}"
        )


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: str,
    lead_update: LeadUpdate,
    repo: Repository = Depends(get_repository)
) -> Dict[str, Any]:
    """
    Update lead information.
    
    - **lead_id**: Lead UUID
    - **name**: New name (optional)
    - **email**: New email (optional)
    - **language**: New language (optional)
    - **status**: New status (optional)
    
    Returns: Updated lead object
    """
    try:
        # Validate UUID
        try:
            UUID(lead_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid lead ID format")
        
        # Check if lead exists
        existing = await repo.get_lead(UUID(lead_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Build update data (only non-None fields)
        updates = {}
        if lead_update.name is not None:
            updates["name"] = lead_update.name
        if lead_update.email is not None:
            updates["email"] = lead_update.email
        if lead_update.language is not None:
            updates["language"] = lead_update.language
        if lead_update.status is not None:
            updates["status"] = lead_update.status
        
        if not updates:
            # No updates, return existing
            logger.info(f"No updates provided for lead: {lead_id}")
            return _format_lead_response(existing)
        
        # Update lead
        updated = await repo.update_lead(UUID(lead_id), **updates)
        
        logger.info(f"Updated lead: {lead_id}")
        return _format_lead_response(updated)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lead: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating lead: {str(e)}"
        )


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: str,
    repo: Repository = Depends(get_repository)
) -> None:
    """
    Delete a lead and all associated data.
    
    - **lead_id**: Lead UUID
    
    Returns: 204 No Content on success
    """
    try:
        # Validate UUID
        try:
            UUID(lead_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid lead ID format")
        
        # Check if lead exists
        existing = await repo.get_lead(UUID(lead_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Delete lead
        deleted = await repo.delete_lead(UUID(lead_id))
        
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete lead")
        
        logger.info(f"Deleted lead: {lead_id}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lead: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting lead: {str(e)}"
        )


@router.get("/search/query", response_model=SearchResponse)
async def search_leads(
    phone: Optional[str] = Query(None, description="Search by phone"),
    email: Optional[str] = Query(None, description="Search by email"),
    repo: Repository = Depends(get_repository)
) -> Dict[str, Any]:
    """
    Search leads by phone or email.
    
    - **phone**: Phone number to search
    - **email**: Email address to search
    
    At least one search parameter required.
    
    Returns: List of matching leads
    """
    try:
        if not phone and not email:
            raise HTTPException(
                status_code=400,
                detail="At least one search parameter (phone or email) required"
            )
        
        results = []
        
        if phone:
            lead = await repo.get_lead_by_phone(phone)
            if lead:
                results.append(lead)
        
        if email and not phone:  # If phone was already searched, don't duplicate
            # Note: We don't have a get_lead_by_email method, so would need to add it
            # For now, we'll just search by phone
            pass
        
        logger.info(f"Search results: {len(results)} leads found")
        
        return {
            "count": len(results),
            "results": [_format_lead_response(lead) for lead in results]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching leads: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching leads: {str(e)}"
        )


@router.post("/batch-upload/csv", response_model=BatchUploadResponse)
async def batch_upload_csv(
    file: UploadFile = File(..., description="CSV file with leads"),
    repo: Repository = Depends(get_repository)
) -> Dict[str, Any]:
    """
    Bulk import leads from CSV file.
    
    CSV Format:
    ```
    phone,name,email,language
    +919876543210,Rajesh Kumar,rajesh@example.com,hi
    +919876543211,Priya Singh,priya@example.com,en
    ```
    
    Returns: Upload summary (created, duplicates, errors)
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="File must be CSV format"
            )
        
        # Read file
        contents = await file.read()
        text = contents.decode('utf-8')
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(text))
        
        created = 0
        duplicates = 0
        errors = 0
        error_details = []
        
        for row_idx, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            try:
                phone = row.get('phone', '').strip()
                name = row.get('name', '').strip() or None
                email = row.get('email', '').strip() or None
                language = row.get('language', 'hi').strip()
                
                if not phone:
                    raise ValueError("Phone is required")
                
                # Check if exists
                existing = await repo.get_lead_by_phone(phone)
                if existing:
                    duplicates += 1
                    error_details.append({
                        "row": row_idx,
                        "phone": phone,
                        "error": "Lead already exists"
                    })
                    continue
                
                # Create lead
                await repo.create_lead(
                    phone=phone,
                    name=name,
                    email=email,
                    language=language
                )
                created += 1
            
            except Exception as e:
                errors += 1
                error_details.append({
                    "row": row_idx,
                    "phone": row.get('phone'),
                    "error": str(e)
                })
        
        logger.info(f"Batch upload: {created} created, {duplicates} duplicates, {errors} errors")
        
        return {
            "created": created,
            "duplicates": duplicates,
            "errors": errors,
            "error_details": error_details
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@router.post("/batch-upload/json", response_model=BatchUploadResponse)
async def batch_upload_json(
    file: UploadFile = File(..., description="JSON file with leads array"),
    repo: Repository = Depends(get_repository)
) -> Dict[str, Any]:
    """
    Bulk import leads from JSON file.
    
    JSON Format:
    ```json
    [
        {"phone": "+919876543210", "name": "Rajesh Kumar", "email": "rajesh@example.com", "language": "hi"},
        {"phone": "+919876543211", "name": "Priya Singh", "email": "priya@example.com", "language": "en"}
    ]
    ```
    
    Returns: Upload summary (created, duplicates, errors)
    """
    try:
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(
                status_code=400,
                detail="File must be JSON format"
            )
        
        # Read and parse file
        contents = await file.read()
        data = json.loads(contents.decode('utf-8'))
        
        if not isinstance(data, list):
            raise HTTPException(
                status_code=400,
                detail="JSON must be an array of objects"
            )
        
        created = 0
        duplicates = 0
        errors = 0
        error_details = []
        
        for idx, item in enumerate(data, start=1):
            try:
                phone = str(item.get('phone', '')).strip()
                name = str(item.get('name', '')).strip() or None
                email = str(item.get('email', '')).strip() or None
                language = str(item.get('language', 'hi')).strip()
                
                if not phone:
                    raise ValueError("Phone is required")
                
                # Check if exists
                existing = await repo.get_lead_by_phone(phone)
                if existing:
                    duplicates += 1
                    error_details.append({
                        "index": idx,
                        "phone": phone,
                        "error": "Lead already exists"
                    })
                    continue
                
                # Create lead
                await repo.create_lead(
                    phone=phone,
                    name=name,
                    email=email,
                    language=language
                )
                created += 1
            
            except Exception as e:
                errors += 1
                error_details.append({
                    "index": idx,
                    "phone": item.get('phone'),
                    "error": str(e)
                })
        
        logger.info(f"Batch upload: {created} created, {duplicates} duplicates, {errors} errors")
        
        return {
            "created": created,
            "duplicates": duplicates,
            "errors": errors,
            "error_details": error_details
        }
    
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON format"
        )
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


# ==================== HELPER FUNCTIONS ====================

def _format_lead_response(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Format lead database record to response"""
    if not lead:
        return {}
    
    current_score = None
    if lead.get("score_classification"):
        current_score = {
            "id": "",
            "leadId": str(lead.get("id", "")),
            "interestScore": lead.get("interest_score", 0.0),
            "engagementScore": lead.get("engagement_score", 0.0),
            "sentimentScore": lead.get("sentiment_score", 0.0),
            "compositeScore": lead.get("composite_score", 0.0),
            "classification": lead.get("score_classification"),
            "timestamp": _format_datetime(lead.get("score_timestamp"))
        }

    rm_assignment = None
    if lead.get("rm_name"):
        rm_assignment = {
            "id": "",
            "leadId": str(lead.get("id", "")),
            "rmName": lead.get("rm_name"),
            "assignedAt": _format_datetime(lead.get("rm_assigned_at")),
            "converted": lead.get("rm_converted", False)
        }

    return {
        "id": str(lead.get("id", "")),
        "phone": lead.get("phone", ""),
        "name": lead.get("name"),
        "email": lead.get("email"),
        "language": lead.get("language", "hi"),
        "status": lead.get("status", "NEW"),
        "created_at": _format_datetime(lead.get("created_at")),
        "updated_at": _format_datetime(lead.get("updated_at")),
        "currentScore": current_score,
        "rmAssignment": rm_assignment
    }


def _format_dict(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format database record, converting datetime objects to strings"""
    if not data:
        return None
    
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def _format_datetime(dt: Any) -> str:
    """Format datetime object to ISO string"""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt) if dt else ""
