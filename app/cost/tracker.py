import os
import uuid
from datetime import datetime
from supabase import create_client
from app.utils.token_counter import count_tokens, calculate_cost

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def log_query_cost(
    user_id: str,
    session_id: str,
    user_message: str,
    response_text: str,
    working_memory_messages: list,
    episodic_context: str = "",
    longterm_context: str = "",
    model: str = "llama3-70b-groq",
    memory_hit: bool = False,
    memory_layer_used: str = None
):
    """Log complete cost breakdown for one query"""
    
    # Count tokens for each layer
    working_tokens = sum(
        count_tokens(m["content"]) for m in working_memory_messages
    )
    episodic_tokens = count_tokens(episodic_context)
    longterm_tokens = count_tokens(longterm_context)
    user_tokens = count_tokens(user_message)
    response_tokens = count_tokens(response_text)
    
    total_input_tokens = working_tokens + episodic_tokens + longterm_tokens + user_tokens
    
    # Calculate actual cost
    cost_data = calculate_cost(total_input_tokens, response_tokens, model)
    actual_cost = cost_data["actual_cost"]
    
    # Calculate naive cost (if no memory management — full history sent every time)
    # Assume naive approach would send 3x more tokens on average
    naive_input_tokens = total_input_tokens * 3
    naive_cost_data = calculate_cost(naive_input_tokens, response_tokens, model)
    naive_cost = naive_cost_data["actual_cost"]
    
    cost_saved = naive_cost - actual_cost
    savings_percent = (cost_saved / naive_cost * 100) if naive_cost > 0 else 0
    
    # Save to PostgreSQL
    log = {
        "user_id": user_id,
        "query_id": str(uuid.uuid4()),
        "session_id": session_id,
        "working_memory_tokens": working_tokens,
        "episodic_memory_tokens": episodic_tokens,
        "longterm_memory_tokens": longterm_tokens,
        "user_message_tokens": user_tokens,
        "response_tokens": response_tokens,
        "total_tokens": total_input_tokens + response_tokens,
        "actual_cost": actual_cost,
        "naive_cost": naive_cost,
        "cost_saved": cost_saved,
        "savings_percent": round(savings_percent, 2),
        "model_used": model,
        "memory_hit": memory_hit,
        "memory_layer_used": memory_layer_used
    }
    
    supabase.table("cost_logs").insert(log).execute()
    return log

async def get_cost_analytics(user_id: str, days: int = 30) -> dict:
    """Get aggregated cost analytics for dashboard"""
    from datetime import datetime, timedelta

    result = supabase.table("cost_logs")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("timestamp", desc=False)\
        .limit(500)\
        .execute()

    logs = result.data

    if not logs:
        return {
            "total_cost": 0,
            "total_saved": 0,
            "total_queries": 0,
            "avg_savings_percent": 0,
            "memory_hit_rate": 0,
            "logs": [],
            "daily_breakdown": [],
            "token_breakdown": [],
            "model_usage": []
        }

    total_cost = sum(l["actual_cost"] or 0 for l in logs)
    total_saved = sum(l["cost_saved"] or 0 for l in logs)
    total_queries = len(logs)
    avg_savings = sum(l["savings_percent"] or 0 for l in logs) / total_queries
    memory_hits = sum(1 for l in logs if l["memory_hit"])
    memory_hit_rate = (memory_hits / total_queries * 100) if total_queries > 0 else 0

    # Daily breakdown for bar chart
    daily = {}
    for log in logs:
        day = log["timestamp"][:10]  # YYYY-MM-DD
        if day not in daily:
            daily[day] = {"date": day, "actual_cost": 0, "naive_cost": 0, "queries": 0, "tokens": 0}
        daily[day]["actual_cost"] += log["actual_cost"] or 0
        daily[day]["naive_cost"] += log["naive_cost"] or 0
        daily[day]["queries"] += 1
        daily[day]["tokens"] += log["total_tokens"] or 0

    daily_breakdown = list(daily.values())[-14:]  # last 14 days

    # Token layer breakdown
    token_breakdown = []
    for log in logs[-20:]:  # last 20 queries
        token_breakdown.append({
            "query": log["timestamp"][11:16],  # HH:MM
            "working": log["working_memory_tokens"] or 0,
            "episodic": log["episodic_memory_tokens"] or 0,
            "longterm": log["longterm_memory_tokens"] or 0,
            "response": log["response_tokens"] or 0,
        })

    # Model usage for pie chart
    model_counts = {}
    for log in logs:
        model = log["model_used"] or "unknown"
        model_counts[model] = model_counts.get(model, 0) + 1

    model_usage = [{"name": k, "value": v} for k, v in model_counts.items()]

    return {
        "total_cost": round(total_cost, 6),
        "total_saved": round(total_saved, 6),
        "total_queries": total_queries,
        "avg_savings_percent": round(avg_savings, 2),
        "memory_hit_rate": round(memory_hit_rate, 2),
        "logs": logs[-50:],
        "daily_breakdown": daily_breakdown,
        "token_breakdown": token_breakdown,
        "model_usage": model_usage
    }