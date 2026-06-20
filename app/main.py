import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routes import chat, memory, cost, keys

app = FastAPI(title="MemVault API", version="1.0.0")

frontend_url = os.getenv("FRONTEND_URL")
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://euetozhnussdkgljzrwx.supabase.co",
]
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat.router,   prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(cost.router,   prefix="/api")
app.include_router(keys.router,   prefix="/api")

@app.get("/")
def health_check():
    return {"status": "MemVault API running ✅", "version": "1.0.0"}