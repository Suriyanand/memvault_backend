import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
from app.utils.encryption import encrypt_key
import uuid

router = APIRouter()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

class ApiKeyRequest(BaseModel):
    user_id: str
    groq_key: str

@router.post("/save-key")
async def save_api_key(request: ApiKeyRequest):
    try:
        # Validate UUID format before hitting DB
        try:
            uuid.UUID(str(request.user_id))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid user_id format. Must be a valid UUID from Supabase auth."
            )

        encrypted = encrypt_key(request.groq_key)

        existing = supabase.table("user_api_keys")\
            .select("id")\
            .eq("user_id", request.user_id)\
            .execute()

        if existing.data:
            supabase.table("user_api_keys")\
                .update({"groq_key_encrypted": encrypted})\
                .eq("user_id", request.user_id)\
                .execute()
        else:
            supabase.table("user_api_keys")\
                .insert({
                    "user_id": request.user_id,
                    "groq_key_encrypted": encrypted
                })\
                .execute()

        return {"message": "API key saved successfully ✅"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
