import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routes import chat, memory, cost, keys

app = FastAPI(title="MemVault API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://memvault.vercel.app",        # ← your Vercel URL
        "https://memvault-*.vercel.app",      # ← preview deployments
    ],
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