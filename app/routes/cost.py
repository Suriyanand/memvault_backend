from fastapi import APIRouter
from app.cost.tracker import get_cost_analytics

router = APIRouter()

@router.get("/cost/analytics/{user_id}")
async def get_analytics(user_id: str, days: int = 30):
    data = await get_cost_analytics(user_id, days)
    return data