import os
import sys

# Thêm thư mục backend vào sys.path để có thể import module 'app' khi chạy trực tiếp file main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.config import settings
from app.routers.webhook import router as webhook_router
from app.services.llm_service import generate_response

app = FastAPI(title="Fitman Sportswear Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount thư mục ảnh tĩnh static
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
static_dir = os.path.join(root_dir, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Đăng ký router Facebook Webhook
app.include_router(webhook_router)

class ChatRequest(BaseModel):
    message: str
    messages: Optional[List[Dict[str, Any]]] = []

@app.get("/")
async def root():
    return {
        "brand": "FITMAN",
        "description": "Chatbot thời trang thể thao phong cách Gym CBUM",
        "status": "online",
        "docs": "/docs",
        "webhook_url": "/webhook",
        "chat_test_url": "/api/chat"
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "local_qwen" if settings.USE_LOCAL_LLM else "openai"
    }

@app.post("/api/chat")
async def chat(request: ChatRequest):
    result = await generate_response(request.messages or [], request.message)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True, app_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
