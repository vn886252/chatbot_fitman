import html
import logging
from typing import Optional, Dict, Any, List
import httpx
from app.config import settings
from app.services.order_service import get_daily_summary, get_period_summary

logger = logging.getLogger(__name__)

# Bàn phím nút bấm thường trực dưới màn hình chat Telegram (Reply Keyboard)
REPLY_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 Doanh thu Hôm nay"}, {"text": "📅 Doanh thu 7 Ngày"}],
        [{"text": "🗓️ Doanh thu Tháng này"}, {"text": "❓ Hướng dẫn"}]
    ],
    "resize_keyboard": True,
    "persistent": True
}

# Cụm nút bấm đính kèm ngay dưới tin nhắn báo cáo (Inline Keyboard)
INLINE_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "📊 Hôm nay", "callback_data": "report_today"},
            {"text": "📅 7 Ngày", "callback_data": "report_week"},
            {"text": "🗓️ Tháng này", "callback_data": "report_month"}
        ],
        [
            {"text": "🔄 Làm mới", "callback_data": "report_refresh"}
        ]
    ]
}


async def send_telegram_message(
    text: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[dict] = None,
    chat_id: Optional[str] = None
) -> bool:
    """Gửi tin nhắn qua Telegram Bot API tới shop owner (hỗ trợ kèm bàn phím nút bấm)."""
    target_chat_id = str(chat_id or settings.TELEGRAM_CHAT_ID)
    if not settings.TELEGRAM_BOT_TOKEN or not target_chat_id:
        logger.warning("Telegram Bot Token or Chat ID not configured. Skipping notification.")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                logger.info(f"Telegram message sent successfully to {target_chat_id}.")
                return True
            else:
                logger.error(f"Telegram API error {res.status_code}: {res.text}")
                return False
    except Exception as e:
        logger.error(f"Exception sending Telegram message: {e}")
        return False


async def answer_callback_query(callback_query_id: str, text: Optional[str] = None) -> bool:
    """Xác nhận callback query để tắt trạng thái loading trên nút bấm Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            return res.status_code == 200
    except Exception as e:
        logger.warning(f"Error answering callback query: {e}")
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


async def send_handover_alert(customer_id: str, customer_name: str, event_type: str, user_text: str = "") -> bool:
    """
    Gửi thông báo Telegram khi có sự kiện chuyển giao hoặc người thật can thiệp chat.
    """
    c_name = html.escape(str(customer_name or "Khách hàng"))
    c_id = html.escape(str(customer_id or ""))
    u_text = html.escape(str(user_text or ""))

    timeout_h = getattr(settings, "HANDOVER_TIMEOUT_HOURS", 2)

    if event_type == "customer_requested":
        msg = f"""🔔 <b>YÊU CẦU GẶP NGƯỜI THẬT!</b>
👤 <b>Khách hàng:</b> {c_name}
🆔 <b>ID:</b> <code>{c_id}</code>
💬 <b>Tin nhắn của khách:</b> <i>"{u_text}"</i>

⚠️ <i>Bot đã tạm dừng tự động với khách này trong {timeout_h} giờ. Bạn vui lòng vào Page Inbox để tư vấn nhé!</i>"""

    elif event_type == "human_chatting":
        msg = f"""👤 <b>NHÂN VIÊN ĐANG CHAT VỚI KHÁCH</b>
👤 <b>Khách hàng:</b> {c_name}
🆔 <b>ID:</b> <code>{c_id}</code>
💬 <b>Nội dung vừa gửi:</b> <i>"{u_text}"</i>

⏸️ <i>Bot đã tạm dừng tự động với khách này. Sau {timeout_h} giờ không có tin nhắn người thật, bot sẽ tự động bật lại.</i>"""

    elif event_type == "auto_resumed":
        msg = f"""▶️ <b>BOT ĐÃ TỰ ĐỘNG BẬT LẠI VỚI KHÁCH</b>
👤 <b>Khách hàng:</b> {c_name}
🆔 <b>ID:</b> <code>{c_id}</code>

ℹ️ <i>Đã quá {timeout_h} giờ không có người thật chat. Bot đã tự động hoạt động trở lại!</i>"""

    else:
        msg = f"""ℹ️ <b>THÔNG BÁO HANDOVER</b>
👤 <b>Khách hàng:</b> {c_name} (<code>{c_id}</code>)
💬 <i>{u_text}</i>"""

    return await send_telegram_message(msg)


def format_period_report(summary: dict) -> str:
    """Format báo cáo doanh thu theo khoảng thời gian thành HTML đẹp mắt cho Telegram."""
    period_type = summary.get("period_type", "today")
    start_date = summary.get("start_date", "")
    end_date = summary.get("end_date", "")
    total_orders = summary.get("total_orders", 0)
    total_items = summary.get("total_items", 0)
    total_revenue = summary.get("total_revenue", 0)
    rev_formatted = f"{total_revenue:,}".replace(",", ".")
    orders = summary.get("orders", [])
    daily_breakdown = summary.get("daily_breakdown", {})

    if period_type == "today":
        title = f"📊 <b>BÁO CÁO DOANH THU HÔM NAY ({end_date})</b>"
        body = f"""🛒 <b>Tổng đơn hôm nay:</b> <b>{total_orders}</b> đơn
👕 <b>Tổng sản phẩm:</b> <b>{total_items}</b> món
💰 <b>Tổng doanh thu:</b> <b>{rev_formatted}đ</b>
"""
        if orders:
            body += "\n📋 <b>Chi tiết đơn hàng hôm nay:</b>\n"
            for idx, o in enumerate(orders, 1):
                khach = html.escape(str(o.get("ten_khach_hang", "Khách hàng")))
                sdt = html.escape(str(o.get("so_dien_thoai", "")))
                sl = o.get("so_luong", 0)
                tien = f"{o.get('tong_tien', 0):,}".replace(",", ".")
                body += f"{idx}. <b>Đơn #{idx}</b> ({khach} - {sdt}): {sl} món - <b>{tien}đ</b>\n"
        else:
            body += "\n<i>Hôm nay chưa có đơn hàng nào phát sinh. Chúc shop bội thu! 🔥</i>"

        return f"{title}\n\n{body}"

    elif period_type == "week":
        title = f"📅 <b>TỔNG KẾT DOANH THU 7 NGÀY QUA</b>\n<i>({start_date} đến {end_date})</i>"
        body = f"""🛒 <b>Tổng số đơn:</b> <b>{total_orders}</b> đơn
👕 <b>Tổng sản phẩm:</b> <b>{total_items}</b> món
💰 <b>Tổng doanh thu:</b> <b>{rev_formatted}đ</b>
"""
        if daily_breakdown:
            body += "\n📆 <b>Thống kê theo từng ngày:</b>\n"
            for d, data in daily_breakdown.items():
                d_rev = f"{data.get('revenue', 0):,}".replace(",", ".")
                body += f"  • <b>{d}</b>: {data.get('orders', 0)} đơn ({data.get('items', 0)} món) - <b>{d_rev}đ</b>\n"
        else:
            body += "\n<i>Trong 7 ngày qua chưa ghi nhận đơn hàng nào.</i>"

        return f"{title}\n\n{body}"

    elif period_type == "month":
        title = f"🗓️ <b>TỔNG KẾT DOANH THU THÁNG NÀY</b>\n<i>({start_date} đến {end_date})</i>"
        body = f"""🛒 <b>Tổng số đơn:</b> <b>{total_orders}</b> đơn
👕 <b>Tổng sản phẩm:</b> <b>{total_items}</b> món
💰 <b>Tổng doanh thu:</b> <b>{rev_formatted}đ</b>
"""
        if daily_breakdown:
            body += "\n📆 <b>Thống kê các ngày có đơn:</b>\n"
            for d, data in daily_breakdown.items():
                d_rev = f"{data.get('revenue', 0):,}".replace(",", ".")
                body += f"  • <b>{d}</b>: {data.get('orders', 0)} đơn ({data.get('items', 0)} món) - <b>{d_rev}đ</b>\n"
        else:
            body += "\n<i>Tháng này chưa ghi nhận đơn hàng nào.</i>"

        return f"{title}\n\n{body}"

    return f"📊 <b>DOANH THU:</b> {rev_formatted}đ ({total_orders} đơn)"


async def send_period_report(chat_id: Optional[str] = None, period_type: str = "today") -> bool:
    """Gửi báo cáo doanh thu theo mốc thời gian kèm cụm nút bấm Inline."""
    target_chat_id = str(chat_id or settings.TELEGRAM_CHAT_ID)
    summary = get_period_summary(period_type)
    msg = format_period_report(summary)
    return await send_telegram_message(msg, reply_markup=INLINE_KEYBOARD, chat_id=target_chat_id)


async def send_telegram_menu(chat_id: Optional[str] = None) -> bool:
    """Gửi tin nhắn chào mừng kèm bàn phím Reply Keyboard thường trực."""
    target_chat_id = str(chat_id or settings.TELEGRAM_CHAT_ID)
    welcome_msg = """👋 <b>BẢNG ĐIỀU KHIỂN DOANH THU FITMAN</b> 🏋️‍♂️

Bạn có thể bấm các nút menu bên dưới màn hình hoặc gõ lệnh trực tiếp:
• <b>📊 Doanh thu Hôm nay</b> (hoặc gõ <code>hôm nay</code>, <code>/today</code>)
• <b>📅 Doanh thu 7 Ngày</b> (hoặc gõ <code>1 tuần</code>, <code>/week</code>)
• <b>🗓️ Doanh thu Tháng này</b> (hoặc gõ <code>tháng này</code>, <code>/month</code>)

<i>Bấm nút bên dưới để xem số liệu ngay nhé!</i> 💪"""
    return await send_telegram_message(welcome_msg, reply_markup=REPLY_KEYBOARD, chat_id=target_chat_id)


async def handle_telegram_update(update: dict) -> bool:
    """
    Xử lý update từ Telegram: tin nhắn văn bản, lệnh gõ hoặc sự kiện click nút bấm (callback_query).
    """
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = str(cb.get("id", ""))
        data = str(cb.get("data", ""))
        user_chat_id = str(cb.get("from", {}).get("id", "") or cb.get("message", {}).get("chat", {}).get("id", ""))

        if cb_id:
            await answer_callback_query(cb_id)

        # Kiểm tra quyền admin
        if str(user_chat_id) != str(settings.TELEGRAM_CHAT_ID):
            logger.warning(f"Unauthorized Telegram callback attempt from chat_id={user_chat_id}")
            return False

        if data == "report_today":
            return await send_period_report(user_chat_id, "today")
        elif data == "report_week":
            return await send_period_report(user_chat_id, "week")
        elif data == "report_month":
            return await send_period_report(user_chat_id, "month")
        elif data == "report_refresh":
            return await send_period_report(user_chat_id, "today")

    elif "message" in update:
        msg = update["message"]
        user_chat_id = str(msg.get("chat", {}).get("id", ""))
        text = str(msg.get("text", "")).strip()

        # Kiểm tra quyền admin
        if str(user_chat_id) != str(settings.TELEGRAM_CHAT_ID):
            logger.warning(f"Unauthorized Telegram message from chat_id={user_chat_id}")
            return False

        text_lower = text.lower()

        # Nhận diện lệnh xem Hôm nay
        if any(k in text_lower for k in ["hôm nay", "hom nay", "today", "/today"]):
            return await send_period_report(user_chat_id, "today")

        # Nhận diện lệnh xem 7 ngày / 1 tuần
        elif any(k in text_lower for k in ["7 ngày", "7 ngay", "tuần", "tuan", "1 tuần", "1 tuan", "week", "/week"]):
            return await send_period_report(user_chat_id, "week")

        # Nhận diện lệnh xem Tháng này / 1 tháng
        elif any(k in text_lower for k in ["tháng", "thang", "1 tháng", "1 thang", "tháng này", "thang nay", "month", "/month"]):
            return await send_period_report(user_chat_id, "month")

        # Các trường hợp khác: hiển thị menu chính kèm bàn phím
        else:
            return await send_telegram_menu(user_chat_id)

    return False
