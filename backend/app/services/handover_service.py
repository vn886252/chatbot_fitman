import time
import logging
import re
from collections import OrderedDict
from typing import Dict, Tuple, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Bộ nhớ đệm lưu các message_id (mid) do chính chatbot gửi qua Graph API
# Dùng OrderedDict giới hạn 1000 items để tránh rò rỉ bộ nhớ
_bot_sent_mids: OrderedDict[str, None] = OrderedDict()
_MAX_BOT_MIDS = 1000

# Trạng thái handover theo từng customer_id (sender_id)
# {customer_id: {"paused": bool, "last_activity": float, "reason": str, "human_notified": bool}}
_handover_state: Dict[str, Dict] = {}


def record_bot_sent(mid: str) -> None:
    """Ghi nhận message ID do bot gửi qua Facebook Graph API."""
    if not mid:
        return
    if len(_bot_sent_mids) >= _MAX_BOT_MIDS:
        _bot_sent_mids.popitem(last=False)
    _bot_sent_mids[mid] = None
    _bot_sent_mids.move_to_end(mid)


def is_bot_sent(mid: str) -> bool:
    """Kiểm tra xem message ID có phải do chính bot vừa gửi không."""
    if not mid:
        return False
    return mid in _bot_sent_mids


def pause_bot(customer_id: str, reason: str = "human_requested") -> None:
    """Tạm dừng bot cho một khách hàng cụ thể."""
    now = time.time()
    _handover_state[customer_id] = {
        "paused": True,
        "last_activity": now,
        "reason": reason,
        "human_notified": False
    }
    logger.info(f"[Handover] Paused bot for customer {customer_id}, reason: {reason}")


def record_human_message(customer_id: str) -> bool:
    """
    Ghi nhận tin nhắn từ người thật (Admin/Nhân viên shop nhắn qua Page Inbox).
    Cập nhật thời điểm hoạt động cuối cùng của người thật.
    Trả về True nếu đây là tin nhắn đầu tiên của người thật trong phiên (để báo Telegram).
    """
    now = time.time()
    state = _handover_state.get(customer_id, {})
    is_first = not state.get("human_notified", False)

    _handover_state[customer_id] = {
        "paused": True,
        "last_activity": now,
        "reason": "human_chatting",
        "human_notified": True
    }
    logger.info(f"[Handover] Recorded human message for customer {customer_id}. is_first_notice={is_first}")
    return is_first


def is_bot_paused(customer_id: str) -> Tuple[bool, float]:
    """
    Kiểm tra trạng thái tạm dừng bot cho khách hàng.
    Trả về (True, remaining_seconds) nếu đang bị tạm dừng.
    Trả về (False, 0.0) nếu bot đang hoạt động bình thường hoặc đã quá thời gian chờ (1-2h).
    """
    state = _handover_state.get(customer_id)
    if not state or not state.get("paused", False):
        return False, 0.0

    last_activity = state.get("last_activity", 0)
    timeout_seconds = getattr(settings, "HANDOVER_TIMEOUT_HOURS", 2) * 3600
    elapsed = time.time() - last_activity

    if elapsed >= timeout_seconds:
        unpause_bot(customer_id)
        logger.info(f"[Handover] Auto-resumed bot for customer {customer_id} after {elapsed:.0f}s of human inactivity.")
        return False, 0.0

    remaining = timeout_seconds - elapsed
    return True, remaining


def unpause_bot(customer_id: str) -> None:
    """Bỏ tạm dừng bot cho khách hàng."""
    if customer_id in _handover_state:
        _handover_state[customer_id]["paused"] = False
        logger.info(f"[Handover] Unpaused bot for customer {customer_id}")


def check_human_request_intent(text: str) -> bool:
    """
    Kiểm tra xem câu chat của khách hàng có ý định muốn gặp người thật không.
    Hỗ trợ cả tiếng Việt có dấu và không dấu.
    """
    if not text:
        return False

    text_lower = text.lower().strip()
    
    # Danh sách từ khóa thể hiện ý định muốn chat với người thật
    keywords = [
        "gặp nhân viên", "gap nhan vien",
        "gặp người thật", "gap nguoi that",
        "chat với người", "chat voi nguoi",
        "nói chuyện với người", "noi chuyen voi nguoi",
        "nói chuyện người thật", "noi chuyen nguoi that",
        "gặp admin", "gap admin",
        "gặp chủ shop", "gap chu shop",
        "tư vấn viên", "tu van vien",
        "chuyển nhân viên", "chuyen nhan vien",
        "chuyển người", "chuyen nguoi",
        "gọi người", "goi nguoi",
        "nhân viên đâu", "nhan vien dau",
        "cần người thật", "can nguoi that",
        "cần người hỗ trợ", "can nguoi ho tro",
        "chat với shop", "chat voi shop",
        "người thật đâu", "nguoi that dau",
        "gặp shop", "gap shop",
        "người trực page", "nguoi truc page",
        "không nói chuyện với bot", "khong noi chuyen voi bot",
        "đổi người", "doi nguoi"
    ]

    for kw in keywords:
        if kw in text_lower:
            return True

    return False
