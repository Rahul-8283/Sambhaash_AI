from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
import json

from services.database.supabase_client import get_db_client
from services.database.repository import Repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/summaries", tags=["summaries"])

@router.get("/")
async def get_all_summaries() -> Dict[str, Any]:
    """
    Fetch all call sessions that have AI-generated summaries.
    """
    db_client = None
    try:
        db_client = await get_db_client()
        repository = Repository(db_client)
        
        records = await repository.get_all_summaries()
        
        # Ensure we return valid JSON formats (e.g. converting UUID to str)
        formatted_records = []
        for r in records:
            # If summary is a string (JSON string from DB), parse it
            summary_data = r.get("summary")
            if isinstance(summary_data, str):
                try:
                    summary_data = json.loads(summary_data)
                except:
                    pass
                    
            formatted_records.append({
                "session_id": str(r.get("session_id")),
                "lead_id": str(r.get("lead_id")),
                "lead_name": r.get("lead_name"),
                "lead_phone": r.get("lead_phone"),
                "duration_seconds": r.get("duration_seconds"),
                "classification": r.get("classification"),
                "created_at": r.get("created_at").isoformat() if r.get("created_at") else None,
                "summary": summary_data
            })
            
        return {"data": formatted_records, "total": len(formatted_records)}
    except Exception as e:
        logger.error(f"Error fetching summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
