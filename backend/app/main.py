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
from app.services.telegram_service import (
    send_daily_revenue_report,
    send_telegram_menu,
    handle_telegram_update
)
import httpx
import json
from pathlib import Path

logger = logging.getLogger(__name__)
ICT = timezone(timedelta(hours=7))
REPORT_TRACKER_FILE = Path(__file__).parent / "data" / "last_report.json"


def _get_last_reported_date() -> str:
    try:
        if REPORT_TRACKER_FILE.exists():
            with open(REPORT_TRACKER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_reported_date", "")
    except Exception as e:
        logger.warning(f"Error reading last report file: {e}")
    return ""


def _set_last_reported_date(date_str: str):
    try:
        REPORT_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_reported_date": date_str}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error writing last report file: {e}")


async def _daily_report_scheduler():
    """Tự động gửi báo cáo doanh thu ngày tới Telegram mỗi ngày (giờ VN)."""
    target_hour = getattr(settings, "DAILY_REPORT_HOUR", 22)
    last_reported_date = _get_last_reported_date()

    while True:
        try:
            now = datetime.now(timezone.utc).astimezone(ICT)
            today_str = now.strftime("%Y-%m-%d")

            # Nếu đã đến hoặc qua target_hour và ngày hôm nay chưa báo cáo
            if now.hour >= target_hour and last_reported_date != today_str:
                logger.info(f"Triggering automatic daily revenue report for {today_str} (hour: {now.hour}, target: {target_hour})...")
                sent = await send_daily_revenue_report(today_str)
                if sent:
                    _set_last_reported_date(today_str)
                    last_reported_date = today_str
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in daily report scheduler: {e}")
            await asyncio.sleep(60)


async def _telegram_polling_loop():
    """
    Background polling loop gọi Telegram getUpdates để nhận tin nhắn và nút bấm trực tiếp từ chủ shop.
    Chạy song song, hoạt động ngay cả khi chạy local (không cần IP public hay ngrok).
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.info("Telegram not fully configured, polling loop skipped.")
        return

    offset = 0
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"

    async with httpx.AsyncClient(timeout=35.0) as client:
        while True:
            try:
                params = {"offset": offset, "timeout": 20, "limit": 20}
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    updates = data.get("result", [])
                    for up in updates:
                        up_id = up.get("update_id", 0)
                        offset = max(offset, up_id + 1)
                        try:
                            await handle_telegram_update(up)
                        except Exception as ex:
                            logger.error(f"Error handling telegram update: {ex}")
                elif res.status_code == 409:
                    logger.warning("Telegram getUpdates returned 409 Conflict (Webhook is set elsewhere). Sleeping 60s.")
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in telegram polling loop: {e}")
                await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động background scheduler báo cáo doanh thu
    scheduler_task = asyncio.create_task(_daily_report_scheduler())
    logger.info("Daily revenue report scheduler started (target: 22:00 ICT daily).")

    # Khởi động background polling nhận tin nhắn & nút bấm Telegram từ admin
    telegram_task = asyncio.create_task(_telegram_polling_loop())
    logger.info("Telegram interactive polling loop started.")

    yield

    scheduler_task.cancel()
    telegram_task.cancel()
    try:
        await asyncio.gather(scheduler_task, telegram_task, return_exceptions=True)
    except Exception:
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

@app.post("/api/telegram/webhook")
async def telegram_webhook(update: Dict[str, Any]):
    """Endpoint Webhook tiếp nhận tin nhắn & sự kiện bấm nút từ Telegram Bot."""
    handled = await handle_telegram_update(update)
    return {"status": "ok", "handled": handled}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True, app_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
