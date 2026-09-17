import os
import sys

# Thêm thư mục backend vào sys.path để có thể import module 'app' khi chạy trực tiếp file main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.config import settings
from app.routers.webhook import router as webhook_router
from app.services.llm_service import generate_response
from app.services.telegram_service import send_daily_revenue_report

logger = logging.getLogger(__name__)
ICT = timezone(timedelta(hours=7))


async def _daily_report_scheduler():
    """Tự động gửi báo cáo doanh thu ngày tới Telegram vào 22:00 mỗi ngày (giờ VN)."""
    last_reported_date = ""
    while True:
        try:
            now = datetime.now(timezone.utc).astimezone(ICT)
            today_str = now.strftime("%Y-%m-%d")
            # Kiểm tra nếu là 22:00 và chưa báo cáo ngày hôm nay
            if now.hour == 22 and now.minute == 0 and last_reported_date != today_str:
                logger.info(f"Triggering automatic daily revenue report for {today_str}...")
                await send_daily_revenue_report(today_str)
                last_reported_date = today_str
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in daily report scheduler: {e}")
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động background scheduler báo cáo doanh thu
    scheduler_task = asyncio.create_task(_daily_report_scheduler())
    logger.info("Daily revenue report scheduler started (target: 22:00 ICT daily).")
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Fitman Sportswear Chatbot API", version="1.0.0", lifespan=lifespan)

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
        "chat_test_url": "/api/chat",
        "daily_report_url": "/api/report/today"
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

@app.api_route("/api/report/today", methods=["GET", "POST"])
async def trigger_daily_report():
    """Endpoint thủ công để kích hoạt gửi báo cáo doanh thu hôm nay qua Telegram."""
    sent = await send_daily_revenue_report()
    return {
        "status": "ok" if sent else "error",
        "message": "Báo cáo doanh thu hôm nay đã được gửi qua Telegram!" if sent else "Gửi báo cáo qua Telegram thất bại, vui lòng kiểm tra cấu hình!"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True, app_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
