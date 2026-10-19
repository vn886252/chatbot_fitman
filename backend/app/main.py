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

from fastapi.responses import FileResponse

@app.get("/")
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "brand": "FITMAN",
        "description": "Chatbot thời trang thể thao phong cách Gym CBUM",
        "status": "online",
        "docs": "/docs",
        "webhook_url": "/webhook",
        "chat_test_url": "/api/chat",
        "daily_report_url": "/api/report/today"
    }

@app.get("/thank-you")
@app.get("/thank-you.html")
async def thank_you():
    page_path = os.path.join(static_dir, "thank-you.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return {"status": "ok", "message": "Fitman Thank You Page"}

@app.get("/api/info")
async def api_info():
    return {
        "brand": "FITMAN",
        "description": "Chatbot thời trang thể thao phong cách Gym CBUM",
        "status": "online",
        "docs": "/docs",
        "webhook_url": "/webhook",
        "chat_test_url": "/api/chat",
        "daily_report_url": "/api/report/today"
    }

@app.get("/api/catalog")
async def get_catalog():
    """Endpoint trả về toàn bộ dữ liệu sản phẩm và chính sách giá."""
    catalog_path = os.path.join(os.path.dirname(__file__), "data", "catalog.json")
    new_models_path = os.path.join(os.path.dirname(__file__), "data", "new_models.json")
    individual_path = os.path.join(os.path.dirname(__file__), "data", "catalog_individual.json")
    data = {}
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data["catalog"] = json.load(f)
        except Exception:
            pass
    if os.path.exists(new_models_path):
        try:
            with open(new_models_path, "r", encoding="utf-8") as f:
                data["new_models"] = json.load(f)
        except Exception:
            pass
    if os.path.exists(individual_path):
        try:
            with open(individual_path, "r", encoding="utf-8") as f:
                data["individual_products"] = json.load(f)
        except Exception:
            pass
    return data

@app.get("/api/products")
async def get_products(category: Optional[str] = None):
    """Endpoint trả về danh sách 58+ sản phẩm lẻ chuẩn SEO."""
    individual_path = os.path.join(os.path.dirname(__file__), "data", "catalog_individual.json")
    if os.path.exists(individual_path):
        try:
            with open(individual_path, "r", encoding="utf-8") as f:
                products = json.load(f)
                if category and category != "all":
                    products = [p for p in products if p.get("category") == category]
                return {"success": True, "total": len(products), "products": products}
        except Exception as e:
            logger.error(f"Error reading products: {e}")
    return {"success": False, "total": 0, "products": []}

class CustomOrderRequest(BaseModel):
    ten_khach_hang: str = "Khách hàng"
    so_dien_thoai: str
    dia_chi: str
    mau_ao: str = "Trắng"
    size_ao: str = "M"
    vi_tri_in: str = "Giữa ngực"
    ten_mau_in: str = "Logo Fitman Signature"
    anh_in_url: Optional[str] = ""
    tong_tien: int = 190000
    ghi_chu: Optional[str] = ""

@app.post("/api/custom-order")
async def create_custom_order(order_req: CustomOrderRequest):
    """
    Tiếp nhận đơn hàng tự thiết kế (Custom Studio) từ website.
    Lưu vào orders.json và gửi thông báo đơn hàng kèm chi tiết thiết kế qua Telegram tới chủ shop.
    """
    from app.services.order_service import save_order
    from app.services.telegram_service import send_new_order_notification

    chi_tiet_mon = f"Áo tự thiết kế ({order_req.mau_ao}, Size {order_req.size_ao}, In {order_req.vi_tri_in}: {order_req.ten_mau_in})"
    if order_req.ghi_chu:
        chi_tiet_mon += f" [Ghi chú: {order_req.ghi_chu}]"

    order_payload = {
        "ten_khach_hang": order_req.ten_khach_hang,
        "so_dien_thoai": order_req.so_dien_thoai,
        "dia_chi": order_req.dia_chi,
        "so_luong": 1,
        "tong_tien": order_req.tong_tien,
        "danh_sach_mon": [chi_tiet_mon],
        "loai_don": "custom_design",
        "custom_details": {
            "mau_ao": order_req.mau_ao,
            "size_ao": order_req.size_ao,
            "vi_tri_in": order_req.vi_tri_in,
            "ten_mau_in": order_req.ten_mau_in,
            "anh_in_url": order_req.anh_in_url
        }
    }

    try:
        saved_order = save_order(order_payload)
        await send_new_order_notification(saved_order)
        return {
            "success": True,
            "order_id": saved_order.get("id"),
            "order_number": saved_order.get("order_number_today"),
            "message": "Đơn hàng tự thiết kế đã được ghi nhận thành công! Shop sẽ liên hệ xác nhận và tiến hành in ngay."
        }
    except Exception as e:
        logger.error(f"Error creating custom order: {e}")
        return {
            "success": False,
            "error": str(e)
        }

class QuickOrderItem(BaseModel):
    id: Optional[str] = ""
    name: str
    size: str = "L"
    qty: int = 1
    price: int = 150000
    image: Optional[str] = ""

class QuickOrderRequest(BaseModel):
    customer_name: str
    customer_phone: str
    shipping_address: str
    payment_method: str = "COD"  # "COD" | "TECHCOMBANK" | "MOMO"
    items: List[QuickOrderItem] = []
    total_amount: int = 0
    note: Optional[str] = ""

@app.post("/api/quick-order")
async def create_quick_order(order_req: QuickOrderRequest):
    """
    Tiếp nhận đơn hàng nhanh trực tiếp từ website không cần chuyển qua Facebook.
    Chỉ cần: Họ tên người nhận, Số điện thoại và Địa chỉ giao hàng.
    Thanh toán: COD, Chuyển khoản Techcombank, hoặc MoMo.
    Tự động đồng bộ vào hệ thống đơn hàng và gửi thông báo Telegram cho chủ shop.
    """
    from app.services.order_service import save_order
    from app.services.telegram_service import send_new_order_notification

    # Chuẩn hoá danh sách món & chi tiết size
    danh_sach_mon = []
    items_detail = []
    so_luong = 0
    for it in order_req.items:
        qty = max(1, int(it.qty))
        size_str = (it.size or "L").upper()
        danh_sach_mon.append(f"{it.name} (Size {size_str}) x{qty}")
        items_detail.append({
            "id": it.id,
            "name": it.name,
            "size": size_str,
            "qty": qty,
            "price": it.price,
            "image": it.image
        })
        so_luong += qty

    if not danh_sach_mon:
        danh_sach_mon = ["Combo Áo Thun Fitman Oversize"]
        so_luong = 1

    payment_method_display = {
        "COD": "💵 COD (Thanh toán khi nhận)",
        "TECHCOMBANK": "🏦 Techcombank (3386111168 - HO KINH DOANH CUA HANG FITMAN)",
        "MOMO": "📱 Ví MoMo (0794763225 - HO KINH DOANH CUA HANG FITMAN)"
    }.get(order_req.payment_method.upper(), order_req.payment_method)

    note_text = f"[{payment_method_display}]"
    if order_req.note:
        note_text += f" {order_req.note}"

    order_payload = {
        "ten_khach_hang": order_req.customer_name,
        "so_dien_thoai": order_req.customer_phone,
        "dia_chi": order_req.shipping_address,
        "so_luong": so_luong,
        "tong_tien": order_req.total_amount,
        "danh_sach_mon": danh_sach_mon,
        "items_detail": items_detail,
        "phuong_thuc_thanh_toan": order_req.payment_method.upper(),
        "ghi_chu": note_text,
        "trang_thai": "Đã tiếp nhận",
        "force_new": True
    }

    try:
        saved_order = save_order(order_payload)
        if not saved_order:
            return {"success": False, "error": "Thông tin đặt hàng không hợp lệ. Vui lòng kiểm tra lại số điện thoại hoặc địa chỉ."}

        await send_new_order_notification(saved_order)
        return {
            "success": True,
            "order_id": saved_order.get("id"),
            "order_number": saved_order.get("order_number_today"),
            "order": saved_order,
            "message": "Đơn hàng của bạn đã được ghi nhận thành công! Fitman sẽ đóng gói và gửi hàng sớm nhất."
        }
    except Exception as e:
        logger.error(f"Error creating quick order: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/order/{order_id}")
async def get_order_tracking(order_id: str):
    """Lấy thông tin chi tiết đơn hàng để hiển thị tracking trên trang Cảm ơn."""
    from app.services.order_service import get_order_by_id
    order = get_order_by_id(order_id)
    if not order:
        return {"success": False, "error": "Không tìm thấy đơn hàng với mã này."}
    return {"success": True, "order": order}


@app.get("/api/payment/vietqr")
async def get_vietqr_info(amount: int = 190000, memo: str = "FITMAN CUST"):
    """Sinh URL mã QR VietQR tự động để thanh toán trước đơn in theo yêu cầu."""
    bank_bin = getattr(settings, "BANK_BIN", "MB")
    acc_no = getattr(settings, "BANK_ACCOUNT_NO", "0901234567")
    acc_name = getattr(settings, "BANK_ACCOUNT_NAME", "FITMAN SPORTSWEAR")
    qr_url = f"https://img.vietqr.io/image/{bank_bin}-{acc_no}-compact2.png?amount={amount}&addInfo={memo}&accountName={acc_name}"
    return {
        "bank_bin": bank_bin,
        "account_no": acc_no,
        "account_name": acc_name,
        "amount": amount,
        "memo": memo,
        "qr_image_url": qr_url
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "local_qwen" if settings.USE_LOCAL_LLM else "openai"
    }

@app.get("/ping")
async def ping():
    return {
        "status": "pong",
        "timestamp": datetime.now(timezone.utc).astimezone(ICT).isoformat()
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
