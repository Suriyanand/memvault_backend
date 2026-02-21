import json
import os
from upstash_redis import Redis

redis = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL"),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
)

WORKING_MEMORY_LIMIT = int(os.getenv("WORKING_MEMORY_LIMIT", 10))
WORKING_MEMORY_TTL = int(os.getenv("WORKING_MEMORY_TTL", 1800))

def get_session_key(user_id: str, session_id: str) -> str:
    return f"session:{user_id}:{session_id}"

async def get_working_memory(user_id: str, session_id: str) -> list:
    """Get all messages from current session"""
    key = get_session_key(user_id, session_id)
    data = redis.get(key)
    if data:
        return json.loads(data)
    return []

async def add_to_working_memory(
    user_id: str,
    session_id: str,
    role: str,
    content: str
) -> list:
    """Add a message to working memory"""
    key = get_session_key(user_id, session_id)
    messages = await get_working_memory(user_id, session_id)
    
    messages.append({
        "role": role,
        "content": content
    })
    
    # Store back with TTL
    redis.setex(key, WORKING_MEMORY_TTL, json.dumps(messages))
    
    return messages

async def clear_working_memory(user_id: str, session_id: str):
    """Clear session after summarization"""
    key = get_session_key(user_id, session_id)
    redis.delete(key)

async def is_memory_full(user_id: str, session_id: str) -> bool:
    """Check if working memory hit limit"""
    messages = await get_working_memory(user_id, session_id)
    return len(messages) >= WORKING_MEMORY_LIMIT

async def get_all_sessions(user_id: str) -> list:
    """Get all active session IDs for a user"""
    pattern = f"session:{user_id}:*"
    keys = redis.keys(pattern)
    sessions = []
    for key in keys:
        session_id = key.split(":")[-1]
        sessions.append(session_id)
    return sessions