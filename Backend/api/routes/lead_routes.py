from fastapi import APIRouter

router = APIRouter(prefix="/api/leads", tags=["Leads"])

@router.get("/")
async def list_leads():
    return {"message": "Lead management coming soon", "leads": []}

@router.post("/")
async def create_lead():
    return {"message": "Lead created"}
