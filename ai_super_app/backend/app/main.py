"""
AI Super App - Main FastAPI Application
"""
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.models import create_tables, SessionLocal
from app.auth import create_admin_user
from app.routers import auth, chat, generate, web_access, vpn

app = FastAPI(
    title="AI Super App",
    description="AI application with multi-model routing, image/video generation, web access & VPN",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    create_tables()
    db = SessionLocal()
    try:
        create_admin_user(db)
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(generate.router)
app.include_router(web_access.router)
app.include_router(vpn.router)


@app.get("/")
async def root():
    return {
        "app": "AI Super App",
        "version": "1.0.0",
        "features": [
            "AI Chat (GPT-4, Claude, Gemini, Llama, Offline)",
            "Image Generation (DALL-E, Stability, Replicate)",
            "Video Generation (Runway, Stable Video Diffusion)",
            "Web Access with VPN",
            "Smart AI Router",
            "Offline Mode",
            "JWT Authentication"
        ],
        "status": "running",
        "admin_user": "admin@1234"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
