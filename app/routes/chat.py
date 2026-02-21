import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import Groq
from supabase import create_client

from app.memory.working import get_working_memory, add_to_working_memory
from app.memory.episodic import get_recent_episodic_memories
from app.memory.longterm import search_longterm_memory
from app.memory.scheduler import run_memory_lifecycle
from app.cost.tracker import log_query_cost
from app.cost.router import get_model_for_query, calculate_routing_savings
from app.utils.encryption import decrypt_key
from app.utils.token_counter import count_tokens

router = APIRouter()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = None
    user_id: str

@router.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    user_id    = request.user_id

    try:
        # Step 1 — Get user's API key
        key_result = supabase.table("user_api_keys")\
            .select("groq_key_encrypted")\
            .eq("user_id", user_id)\
            .single().execute()

        if not key_result.data or not key_result.data.get("groq_key_encrypted"):
            raise HTTPException(status_code=400, detail="No API key found. Add your Groq key in settings.")

        groq_api_key = decrypt_key(key_result.data["groq_key_encrypted"])

        # Step 2 — Smart model routing 🔀
        model_config = get_model_for_query(request.message)
        model_id     = model_config["model_id"]
        complexity   = model_config["complexity"]
        max_tokens   = model_config["max_tokens"]

        groq_client = Groq(api_key=groq_api_key)

        # Step 3 — Fetch all memory layers
        working_memory  = await get_working_memory(user_id, session_id)
        episodic_memories = await get_recent_episodic_memories(user_id, limit=3)
        longterm_facts  = await search_longterm_memory(user_id, request.message, top_k=3)

        episodic_context = ""
        if episodic_memories:
            episodic_context = "PAST CONVERSATION SUMMARIES:\n" + \
                "\n".join([f"- {m['summary']}" for m in episodic_memories])

        longterm_context = ""
        if longterm_facts:
            longterm_context = "WHAT I KNOW ABOUT YOU:\n" + \
                "\n".join([f"- {fact}" for fact in longterm_facts])

        memory_hit        = bool(episodic_memories or longterm_facts)
        memory_layer_used = "longterm" if longterm_facts else ("episodic" if episodic_memories else None)

        # Step 4 — Build prompt
        system_prompt = "You are a helpful AI assistant with persistent memory."
        if longterm_context:  system_prompt += f"\n\n{longterm_context}"
        if episodic_context:  system_prompt += f"\n\n{episodic_context}"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(working_memory)
        messages.append({"role": "user", "content": request.message})

        # Step 5 — Call routed model
        response = groq_client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens
        )
        assistant_message = response.choices[0].message.content

        # Step 6 — Save to working memory
        await add_to_working_memory(user_id, session_id, "user",      request.message)
        await add_to_working_memory(user_id, session_id, "assistant", assistant_message)

        # Step 7 — Log cost
        cost_log = await log_query_cost(
            user_id=user_id,
            session_id=session_id,
            user_message=request.message,
            response_text=assistant_message,
            working_memory_messages=working_memory,
            episodic_context=episodic_context,
            longterm_context=longterm_context,
            model=model_config["label"],
            memory_hit=memory_hit,
            memory_layer_used=memory_layer_used
        )

        # Step 8 — Calculate routing savings
        routing_savings = calculate_routing_savings(
            request.message,
            cost_log["working_memory_tokens"] + cost_log["user_message_tokens"],
            cost_log["response_tokens"],
            model_config["label"]
        )

        # Step 9 — Memory lifecycle
        await run_memory_lifecycle(user_id, session_id, groq_api_key)

        return {
            "response":    assistant_message,
            "session_id":  session_id,
            "routing": {
                "complexity":          complexity,
                "model_used":          model_config["label"],
                "model_id":            model_id,
                "routing_saved":       routing_savings["routing_saved"],
                "routing_savings_pct": routing_savings["routing_savings_pct"],
            },
            "memory_used": {
                "working_messages":  len(working_memory),
                "episodic_summaries": len(episodic_memories),
                "longterm_facts":    len(longterm_facts),
                "memory_hit":        memory_hit,
                "memory_layer_used": memory_layer_used,
            },
            "cost": {
                "total_tokens":    cost_log["total_tokens"],
                "actual_cost":     cost_log["actual_cost"],
                "cost_saved":      cost_log["cost_saved"],
                "savings_percent": cost_log["savings_percent"],
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))