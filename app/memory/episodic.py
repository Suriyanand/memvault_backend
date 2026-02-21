import os
import uuid
from datetime import datetime, timedelta
from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def save_episodic_memory(
    user_id: str,
    session_id: str,
    summary: str,
    importance_score: float = 0.5
):
    """Save a conversation summary to episodic memory"""
    data = {
        "user_id": user_id,
        "session_id": session_id,
        "summary": summary,
        "importance_score": importance_score
    }
    result = supabase.table("episodic_memories").insert(data).execute()
    return result.data

async def get_recent_episodic_memories(user_id: str, limit: int = 5) -> list:
    """Get recent summaries for context injection"""
    result = supabase.table("episodic_memories")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("is_archived", False)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()
    return result.data

async def get_old_episodic_memories(user_id: str, days: int = 7) -> list:
    """Get memories older than N days for promotion to long-term"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    result = supabase.table("episodic_memories")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("is_archived", False)\
        .lt("created_at", cutoff)\
        .execute()
    return result.data

async def archive_episodic_memory(memory_id: str):
    """Mark memory as archived after promoting to long-term"""
    supabase.table("episodic_memories")\
        .update({"is_archived": True})\
        .eq("id", memory_id)\
        .execute()