from fastapi import APIRouter
from app.memory.working import get_working_memory
from app.memory.episodic import get_recent_episodic_memories
from app.memory.longterm import search_longterm_memory, delete_user_memory
import os
from supabase import create_client

router = APIRouter()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

@router.get("/memory/{user_id}")
async def get_all_memory(user_id: str, session_id: str = None):
    working = []
    if session_id:
        working = await get_working_memory(user_id, session_id)

    episodic = await get_recent_episodic_memories(user_id, limit=10)
    longterm = await search_longterm_memory(user_id, "user profile facts", top_k=10)

    return {
        "working_memory": working or [],
        "episodic_memory": episodic or [],
        "longterm_memory": longterm or []
    }

@router.get("/memory/graph/{user_id}")
async def get_memory_graph(user_id: str):
    """Build node graph data from all memory layers"""

    episodic = await get_recent_episodic_memories(user_id, limit=15)
    longterm = await search_longterm_memory(user_id, "user facts skills projects", top_k=15)

    nodes = []
    links = []

    # Central user node
    nodes.append({
        "id": "user",
        "label": "You",
        "type": "user",
        "size": 28
    })

    # Layer hub nodes
    nodes.append({"id": "hub_episodic", "label": "Episodic\nMemory",  "type": "hub_episodic",  "size": 20})
    nodes.append({"id": "hub_longterm", "label": "Long-Term\nMemory", "type": "hub_longterm", "size": 20})

    # Connect hubs to user
    links.append({"source": "user", "target": "hub_episodic",  "strength": 0.8})
    links.append({"source": "user", "target": "hub_longterm", "strength": 0.8})

    # Episodic memory nodes
    for i, mem in enumerate(episodic):
        node_id = f"episodic_{i}"
        # Truncate summary for label
        label = (mem.get("summary") or "")[:40] + "..."
        nodes.append({
            "id":         node_id,
            "label":      label,
            "type":       "episodic",
            "size":       12 + (mem.get("importance_score", 0.5) * 10),
            "full_text":  mem.get("summary", ""),
            "date":       mem.get("created_at", "")[:10]
        })
        links.append({"source": "hub_episodic", "target": node_id, "strength": 0.5})

    # Long-term memory nodes
    for i, fact in enumerate(longterm):
        node_id = f"longterm_{i}"
        label   = str(fact)[:35] + "..." if len(str(fact)) > 35 else str(fact)
        nodes.append({
            "id":        node_id,
            "label":     label,
            "type":      "longterm",
            "size":      14,
            "full_text": str(fact)
        })
        links.append({"source": "hub_longterm", "target": node_id, "strength": 0.5})

        # Cross-link: connect long-term facts to related episodic nodes
        for j, mem in enumerate(episodic):
            fact_str    = str(fact).lower()
            summary_str = (mem.get("summary") or "").lower()
            # If they share keywords → draw a cross link
            fact_words = set(fact_str.split())
            summ_words = set(summary_str.split())
            overlap    = len(fact_words & summ_words)
            if overlap >= 3:
                links.append({
                    "source":   f"longterm_{i}",
                    "target":   f"episodic_{j}",
                    "strength": 0.2
                })

    return {"nodes": nodes, "links": links}

@router.delete("/memory/{user_id}")
async def clear_memory(user_id: str):
    await delete_user_memory(user_id)
    return {"message": "Long-term memory cleared"}