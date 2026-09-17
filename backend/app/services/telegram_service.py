import html
import logging
from typing import Optional, Dict, Any
import httpx
from app.config import settings
from app.services.order_service import get_daily_summary

logger = logging.getLogger(__name__)


async def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    """Gửi tin nhắn qua Telegram Bot API tới shop owner."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram Bot Token or Chat ID not configured. Skipping notification.")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                logger.info("Telegram message sent successfully.")
                return True
            else:
                logger.error(f"Telegram API error {res.status_code}: {res.text}")
                return False
    except Exception as e:
        logger.error(f"Exception sending Telegram message: {e}")
        return False


async def send_new_order_notification(order: Dict[str, Any]) -> bool:
    """
    Format và gửi thông báo đơn hàng mới tới Telegram kèm số thứ tự đơn trong ngày.
    """
    order_id = html.escape(str(order.get("id", "")))
    order_num = order.get("order_number_today", 1)
    ten_khach = html.escape(str(order.get("ten_khach_hang", "Khách hàng")))
    sdt = html.escape(str(order.get("so_dien_thoai", "")))
    dia_chi = html.escape(str(order.get("dia_chi", "")))
    so_luong = order.get("so_luong", 0)
    tong_tien = order.get("tong_tien", 0)
    created_at = html.escape(str(order.get("created_at", "")))

    formatted_tien = f"{tong_tien:,}".replace(",", ".")

    danh_sach = order.get("danh_sach_mon", [])
    if isinstance(danh_sach, str):
        danh_sach = [danh_sach]

    items_html = "\n".join([f"  • {html.escape(str(m))}" for m in danh_sach])

    freeship_text = " (Freeship)" if so_luong >= 2 else " (+30k ship)"

    msg = f"""🔥 <b>ĐƠN HÀNG MỚI (ĐƠN #{order_num} TRONG NGÀY)</b> 🔥
🔖 <b>Mã đơn:</b> <code>{order_id}</code>

👤 <b>Khách hàng:</b> {ten_khach}
📞 <b>SĐT:</b> <code>{sdt}</code>
📍 <b>Địa chỉ:</b> {dia_chi}
📦 <b>Số lượng:</b> {so_luong} món
📋 <b>Chi tiết món:</b>
{items_html}

💰 <b>Tổng tiền:</b> <b>{formatted_tien}đ</b>{freeship_text}
⏰ <b>Thời gian:</b> {created_at}

<i>Chatbot đã ghi nhận đơn #{order_num} trong ngày và lưu hệ thống!</i> 💪"""

    return await send_telegram_message(msg)


async def send_daily_revenue_report(target_date: Optional[str] = None) -> bool:
    """
    Format và gửi báo cáo tổng kết doanh thu ngày tới Telegram lúc 22:00.
    """
    summary = get_daily_summary(target_date)
    date_str = summary.get("date", "")
    total_orders = summary.get("total_orders", 0)
    total_items = summary.get("total_items", 0)
    total_revenue = summary.get("total_revenue", 0)
    orders = summary.get("orders", [])

    formatted_rev = f"{total_revenue:,}".replace(",", ".")

    if total_orders == 0:
        msg = f"""📊 <b>BÁO CÁO DOANH THU NGÀY {date_str} (LÚC 22:00)</b>

🛒 <b>Tổng đơn:</b> 0 đơn
👕 <b>Tổng sản phẩm:</b> 0 món
💰 <b>Doanh thu:</b> 0đ

<i>Hôm nay chưa có đơn hàng nào hoàn tất. Chúc shop ngày mai bội thu đơn! 🔥</i>"""
        return await send_telegram_message(msg)

    orders_detail = []
    for idx, o in enumerate(orders, 1):
        t_tien = f"{o.get('tong_tien', 0):,}".replace(",", ".")
        khach = html.escape(str(o.get('ten_khach_hang', 'Khách hàng')))
        sdt = html.escape(str(o.get('so_dien_thoai', '')))
        sl = o.get('so_luong', 0)
        orders_detail.append(f"{idx}. <b>Đơn #{idx}</b> ({khach} - {sdt}): {sl} món - <b>{t_tien}đ</b>")

    detail_str = "\n".join(orders_detail)

    msg = f"""📊 <b>TỔNG KẾT DOANH THU NGÀY {date_str} (LÚC 22:00)</b> 📊

🛒 <b>Tổng số đơn:</b> <b>{total_orders}</b> đơn
👕 <b>Tổng sản phẩm bán ra:</b> <b>{total_items}</b> món
💰 <b>Tổng doanh thu:</b> <b>{formatted_rev}đ</b>

📋 <b>Danh sách đơn hôm nay:</b>
{detail_str}

💪 <i>FITMAN chúc shop ngày mai bội thu đơn!</i> 🔥"""

    return await send_telegram_message(msg)
