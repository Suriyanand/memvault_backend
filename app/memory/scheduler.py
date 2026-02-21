import os
from groq import Groq
from app.memory.working import get_working_memory, clear_working_memory, is_memory_full
from app.memory.episodic import save_episodic_memory, get_old_episodic_memories, archive_episodic_memory
from app.memory.longterm import save_longterm_memory
import json

async def summarize_conversation(messages: list, groq_api_key: str) -> tuple:
    """Use Groq to summarize a conversation — uses USER's api key"""
    groq_client = Groq(api_key=groq_api_key)   # ✅ user's key

    conversation_text = "\n".join([
        f"{m['role'].upper()}: {m['content']}" for m in messages
    ])

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Summarize this conversation in 3-4 key points.
Focus on: what the user is working on, problems discussed, solutions found, user preferences shown.
Be concise. Output as plain text bullet points.

CONVERSATION:
{conversation_text}"""
        }],
        max_tokens=300
    )

    summary = response.choices[0].message.content
    importance = min(1.0, len(summary) / 500)
    return summary, importance


async def extract_user_facts(summary: str, groq_api_key: str) -> dict:
    """Extract permanent user facts — uses USER's api key"""
    groq_client = Groq(api_key=groq_api_key)   # ✅ user's key

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""From this conversation summary, extract permanent facts about the user.
Return ONLY valid JSON, nothing else.

Summary: {summary}

Return JSON with these fields (use null if not mentioned):
{{
  "name": null,
  "skills": [],
  "current_projects": [],
  "goals": [],
  "preferences": [],
  "background": null
}}"""
        }],
        max_tokens=200
    )

    try:
        facts_text = response.choices[0].message.content.strip()
        if "```" in facts_text:
            facts_text = facts_text.split("```")[1]
            if facts_text.startswith("json"):
                facts_text = facts_text[4:]
        return json.loads(facts_text)
    except:
        return {}


async def run_memory_lifecycle(user_id: str, session_id: str, groq_api_key: str):
    """Main scheduler — promote memories up the chain using user's key"""

    # Step 1: Check if working memory is full
    if await is_memory_full(user_id, session_id):
        messages = await get_working_memory(user_id, session_id)

        if messages:
            # Summarize and push to episodic
            summary, importance = await summarize_conversation(messages, groq_api_key)
            await save_episodic_memory(user_id, session_id, summary, importance)
            await clear_working_memory(user_id, session_id)
            print(f"✅ Promoted working memory → episodic for user {user_id}")

    # Step 2: Promote old episodic → long-term
    old_memories = await get_old_episodic_memories(user_id, days=7)
    for memory in old_memories:
        facts = await extract_user_facts(memory["summary"], groq_api_key)
        if facts:
            await save_longterm_memory(user_id, facts)
        await archive_episodic_memory(memory["id"])
        print(f"✅ Promoted episodic → long-term for user {user_id}")