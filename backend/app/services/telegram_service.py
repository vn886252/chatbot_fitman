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
        [{"text": "🗓️ Doanh thu Tháng này"}, {"text": "👕 Quản lý Mẫu mới"}],
        [{"text": "❓ Hướng dẫn"}]
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
    is_updated = order.get("is_updated", False)

    formatted_tien = f"{tong_tien:,}".replace(",", ".")

    danh_sach = order.get("danh_sach_mon", [])
    if isinstance(danh_sach, str):
        danh_sach = [danh_sach]

    items_html = "\n".join([f"  • {html.escape(str(m))}" for m in danh_sach])

    freeship_text = " (Freeship)" if so_luong >= 2 else " (+30k ship)"

    # Xử lý tiêu đề và lời kết
    if is_updated:
        title = f"🔄 <b>ĐƠN HÀNG ĐÃ ĐƯỢC CẬP NHẬT (ĐƠN #{order_num} TRONG NGÀY)</b> 🔄"
        footer = f"<i>Chatbot đã cập nhật lại chi tiết món và tổng tiền cho đơn #{order_num}!</i> 💪"
    else:
        title = f"🔥 <b>ĐƠN HÀNG MỚI (ĐƠN #{order_num} TRONG NGÀY)</b> 🔥"
        footer = f"<i>Chatbot đã ghi nhận đơn #{order_num} trong ngày và lưu hệ thống!</i> 💪"

    # Xử lý phần hiển thị khách hàng: xóa 'Khách hàng: Khách hàng', thay bằng định danh SĐT
    if not ten_khach or ten_khach.strip() == "" or ten_khach == "Khách hàng":
        customer_info = f"👤 <b>Khách hàng:</b> <code>{sdt}</code>"
    else:
        customer_info = f"👤 <b>Khách hàng:</b> {ten_khach} (<code>{sdt}</code>)"

    msg = f"""{title}
🔖 <b>Mã đơn:</b> <code>{order_id}</code>

{customer_info}
📍 <b>Địa chỉ:</b> {dia_chi}
📦 <b>Số lượng:</b> {so_luong} món
📋 <b>Chi tiết món:</b>
{items_html}

💰 <b>Tổng tiền:</b> <b>{formatted_tien}đ</b>{freeship_text}
⏰ <b>Thời gian:</b> {created_at}

{footer}"""

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
        if not khach or khach.strip() == "" or khach == "Khách hàng":
            orders_detail.append(f"{idx}. <b>Đơn #{idx}</b> (<code>{sdt}</code>): {sl} món - <b>{t_tien}đ</b>")
        else:
            orders_detail.append(f"{idx}. <b>Đơn #{idx}</b> ({khach} - <code>{sdt}</code>): {sl} món - <b>{t_tien}đ</b>")

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
                if not khach or khach.strip() == "" or khach == "Khách hàng":
                    body += f"{idx}. <b>Đơn #{idx}</b> (<code>{sdt}</code>): {sl} món - <b>{tien}đ</b>\n"
                else:
                    body += f"{idx}. <b>Đơn #{idx}</b> ({khach} - <code>{sdt}</code>): {sl} món - <b>{tien}đ</b>\n"
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
    welcome_msg = """👋 <b>BẢNG ĐIỀU KHIỂN FITMAN CHATBOT</b> 🏋️‍♂️

Bạn có thể bấm các nút menu bên dưới màn hình hoặc gõ lệnh trực tiếp:
• <b>📊 Doanh thu Hôm nay</b> (hoặc gõ <code>hôm nay</code>, <code>/today</code>)
• <b>📅 Doanh thu 7 Ngày</b> (hoặc gõ <code>1 tuần</code>, <code>/week</code>)
• <b>🗓️ Doanh thu Tháng này</b> (hoặc gõ <code>tháng này</code>, <code>/month</code>)
• <b>👕 Quản lý Mẫu mới</b> (hoặc gõ <code>mẫu mới</code>, <code>/newmodel</code>)

📸 <b>Thêm mẫu mới 2026:</b>
Chỉ cần gửi ảnh sản phẩm trực tiếp vào chat này (kèm caption nếu muốn)! Bot sẽ tự lưu và cập nhật tối đa 6 mẫu mới nhất để gửi cho khách.

<i>Bấm nút bên dưới để sử dụng ngay!</i> 💪"""
    return await send_telegram_message(welcome_msg, reply_markup=REPLY_KEYBOARD, chat_id=target_chat_id)


async def send_model_management_info(chat_id: Optional[str] = None) -> bool:
    """Gửi danh sách mẫu mới đang hiển thị và hướng dẫn quản lý."""
    target_chat_id = str(chat_id or settings.TELEGRAM_CHAT_ID)
    from app.services.new_models_service import list_all_models
    info = list_all_models()
    new_m = info.get("new", [])
    old_m = info.get("old", [])
    total = info.get("total", 0)

    lines = [
        "👕 <b>DANH SÁCH MẪU MỚI (SLIDING WINDOW)</b>\n",
        f"📊 Tổng số mẫu trong hệ thống: <b>{total}</b>",
        f"🔥 Đang hiển thị khi khách hỏi 'mẫu mới': <b>{len(new_m)}/6 mẫu</b>\n"
    ]

    if new_m:
        lines.append("<b>Mẫu mới đang hiển thị (tối đa 6):</b>")
        for i, m in enumerate(new_m, 1):
            desc = f" ({html.escape(m['description'])})" if m.get("description") else ""
            lines.append(f"{i}. Mã: <code>{m['id']}</code>{desc}")
            lines.append(f"   🖼️ {m['image_url']}")
    else:
        lines.append("<i>Chưa có mẫu mới nào được thêm. Khi khách hỏi mẫu mới, bot sẽ gửi tất cả mẫu hiện có.</i>")

    if old_m:
        lines.append(f"\n📦 <b>Mẫu cũ (đã trượt khỏi cửa sổ 6 mẫu mới nhất):</b>")
        for m in old_m:
            lines.append(f"• Mã: <code>{m['id']}</code> ({m['image_url']})")

    lines.append("\n" + "—" * 20)
    lines.append("📸 <b>Cách thêm mẫu mới:</b>")
    lines.append("Gửi ảnh vào chat này kèm <b>mã mẫu bạn muốn đặt</b> vào ghi chú (caption).")
    lines.append("• <i>Chỉ đặt mã:</i> <code>48</code> hoặc <code>W8</code>, <code>Q8</code>")
    lines.append("• <i>Kèm mô tả:</i> <code>48 Áo CBUM 2026</code> hoặc <code>W8 Áo Wolves punk</code>")
    lines.append("\n❌ <b>Cách xóa mẫu:</b>")
    lines.append("Gửi lệnh: <code>/xoa_mau [mã]</code> (ví dụ: <code>/xoa_mau 48</code>).")

    text = "\n".join(lines)
    return await send_telegram_message(text, reply_markup=REPLY_KEYBOARD, chat_id=target_chat_id)


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

        # 1. Xử lý khi admin gửi ẢNH để thêm mẫu mới
        if "photo" in msg:
            photos = msg.get("photo", [])
            if photos:
                best_photo = photos[-1]
                file_id = best_photo.get("file_id")
                caption = str(msg.get("caption", "")).strip()

                from app.services.new_models_service import parse_model_caption, download_telegram_photo, add_new_model, list_all_models

                model_id, description = parse_model_caption(caption)
                if not model_id:
                    # Chủ shop chưa nhập mã mẫu
                    guide_text = (
                        "⚠️ <b>THIẾU MÃ MẪU!</b>\n\n"
                        "Vui lòng gửi lại ảnh và nhập <b>mã mẫu bạn muốn đặt</b> vào phần ghi chú (caption) của ảnh nha anh.\n\n"
                        "💡 <i>Ví dụ:</i>\n"
                        "• <code>48</code> (chỉ cần nhập số mã)\n"
                        "• <code>48 Áo CBUM 2026</code> (mã + mô tả)\n"
                        "• <code>W8 Áo Wolves punk</code>\n"
                        "• <code>Q8 Quần đùi CBUM đen</code>"
                    )
                    return await send_telegram_message(guide_text, chat_id=user_chat_id)

                saved_url = await download_telegram_photo(file_id, model_id=model_id)
                if saved_url:
                    new_item = add_new_model(saved_url, model_id=model_id, description=description)
                    all_info = list_all_models()
                    new_count = len(all_info.get("new", []))
                    old_count = len(all_info.get("old", []))

                    push_msg = ""
                    if old_count > 0:
                        pushed = all_info["old"][-1]
                        push_msg = f"\nℹ️ <i>Mẫu cũ <code>{pushed['id']}</code> đã được chuyển vào danh mục mẫu cũ.</i>"

                    success_text = (
                        f"✅ <b>ĐÃ LƯU MẪU {new_item['id']} THÀNH CÔNG!</b>\n\n"
                        f"🆔 Mã mẫu: <b>{new_item['id']}</b>\n"
                        f"📝 Mô tả: {html.escape(new_item.get('description', ''))}\n"
                        f"🖼️ Đường dẫn: <code>{new_item['image_url']}</code>\n"
                        f"🔥 Đang hiển thị: <b>{new_count}/6 mẫu mới nhất</b>"
                        f"{push_msg}\n\n"
                        f"💡 Khi khách hỏi 'mẫu mới' hoặc mã '{new_item['id']}', bot sẽ tự động gửi mẫu này!"
                    )
                    return await send_telegram_message(success_text, chat_id=user_chat_id)
                else:
                    return await send_telegram_message("❌ Tải ảnh từ Telegram thất bại. Vui lòng thử lại!", chat_id=user_chat_id)

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

        # Nhận diện lệnh Quản lý mẫu mới
        elif any(k in text_lower for k in ["mẫu mới", "mau moi", "quản lý mẫu", "quan ly mau", "/newmodel", "/mau_moi"]):
            return await send_model_management_info(user_chat_id)

        # Nhận diện lệnh xóa mẫu: /xoa_mau [mã] hoặc xóa mẫu [mã]
        elif text_lower.startswith("/xoa_mau") or text_lower.startswith("/deletemodel") or "xóa mẫu" in text_lower or "xoa mau" in text_lower:
            parts = text.split()
            target_id = ""
            for p in parts:
                p_clean = p.strip(".,:;").upper()
                if p_clean not in ["/XOA_MAU", "/DELETEMODEL", "XÓA", "XOA", "MẪU", "MAU"]:
                    target_id = p_clean
                    break
            if target_id:
                from app.services.new_models_service import remove_model
                success = remove_model(target_id)
                if success:
                    return await send_telegram_message(f"✅ Đã xóa mẫu <code>{target_id}</code> thành công!", chat_id=user_chat_id)
                else:
                    return await send_telegram_message(f"❌ Không tìm thấy mẫu <code>{target_id}</code> trong danh sách!", chat_id=user_chat_id)
            else:
                return await send_telegram_message("⚠️ Vui lòng ghi rõ mã mẫu cần xóa. Ví dụ: <code>/xoa_mau 48</code>", chat_id=user_chat_id)

        # Các trường hợp khác: hiển thị menu chính kèm bàn phím
        else:
            return await send_telegram_menu(user_chat_id)

    return False
