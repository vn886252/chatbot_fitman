import time
import logging
import re
import os
import json
from collections import OrderedDict
from typing import Dict, Tuple, Optional, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

# File lưu trạng thái handover lâu dài: backend/app/data/handover.json
def _get_data_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "handover.json"))

# Bộ nhớ đệm lưu các message_id (mid) do chính chatbot gửi qua Graph API
_bot_sent_mids: OrderedDict[str, None] = OrderedDict()
_MAX_BOT_MIDS = 1000

# Trạng thái handover theo từng customer_id (sender_id)
# {customer_id: {"paused": bool, "last_activity": float, "reason": str, "human_notified": bool}}
_handover_state: Dict[str, Dict] = {}

# Trạng thái tạm dừng toàn bộ (global)
_global_state: Dict[str, Any] = {
    "paused": False,
    "pause_time": 0.0,
    "last_customer_id": ""
}


def _save_state() -> None:
    """Lưu trạng thái handover vào file JSON để bảo toàn khi server restart."""
    data_path = _get_data_path()
    try:
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        data = {
            "global_paused": _global_state.get("paused", False),
            "global_pause_time": _global_state.get("pause_time", 0.0),
            "last_customer_id": _global_state.get("last_customer_id", ""),
            "customers": _handover_state
        }
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"[Handover] Could not save handover state to file: {e}")


def _load_state() -> None:
    """Đọc trạng thái handover từ file JSON khi khởi động."""
    data_path = _get_data_path()
    try:
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _global_state["paused"] = data.get("global_paused", False)
            _global_state["pause_time"] = data.get("global_pause_time", 0.0)
            _global_state["last_customer_id"] = data.get("last_customer_id", "")
            _handover_state.clear()
            _handover_state.update(data.get("customers", {}))
    except Exception as e:
        logger.warning(f"[Handover] Could not load handover state from file: {e}")


# Tự động nạp dữ liệu khi import module
_load_state()


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


def pause_global(reason: str = "admin_requested") -> float:
    """
    Tạm dừng TOÀN BỘ bot (tất cả khách hàng) trong HANDOVER_TIMEOUT_HOURS (mặc định 2 giờ).
    Trả về số giờ timeout.
    """
    now = time.time()
    _global_state["paused"] = True
    _global_state["pause_time"] = now
    _save_state()
    timeout_h = getattr(settings, "HANDOVER_TIMEOUT_HOURS", 2)
    logger.info(f"[Handover] Globally paused bot for {timeout_h}h, reason: {reason}")
    return float(timeout_h)


def unpause_global() -> None:
    """Bỏ tạm dừng toàn bộ bot."""
    _global_state["paused"] = False
    _save_state()
    logger.info("[Handover] Globally unpaused bot")


def unpause_all() -> None:
    """Bật lại toàn bộ bot (cả global và tất cả khách hàng)."""
    _global_state["paused"] = False
    for cid in list(_handover_state.keys()):
        _handover_state[cid]["paused"] = False
    _save_state()
    logger.info("[Handover] Unpaused all (global and all customers)")


def pause_bot(customer_id: str, reason: str = "human_requested") -> None:
    """Tạm dừng bot cho một khách hàng cụ thể."""
    now = time.time()
    _handover_state[customer_id] = {
        "paused": True,
        "last_activity": now,
        "reason": reason,
        "human_notified": False
    }
    _global_state["last_customer_id"] = customer_id
    _save_state()
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
    _global_state["last_customer_id"] = customer_id
    _save_state()
    logger.info(f"[Handover] Recorded human message for customer {customer_id}. is_first_notice={is_first}")
    return is_first


def is_bot_paused(customer_id: str = "") -> Tuple[bool, float]:
    """
    Kiểm tra trạng thái tạm dừng bot:
    1. Kiểm tra tạm dừng toàn bộ (global_paused).
    2. Kiểm tra tạm dừng riêng cho khách hàng (customer_id).
    Trả về (True, remaining_seconds) nếu đang bị tạm dừng.
    Trả về (False, 0.0) nếu bot đang hoạt động bình thường hoặc đã quá thời gian chờ (1-2h).
    """
    timeout_seconds = getattr(settings, "HANDOVER_TIMEOUT_HOURS", 2) * 3600
    now = time.time()

    # 1. Kiểm tra Global Pause
    if _global_state.get("paused"):
        elapsed_global = now - _global_state.get("pause_time", 0.0)
        if elapsed_global < timeout_seconds:
            return True, timeout_seconds - elapsed_global
        else:
            _global_state["paused"] = False
            _save_state()
            logger.info("[Handover] Auto-resumed global bot after timeout.")

    # 2. Kiểm tra Per-Customer Pause
    if customer_id:
        state = _handover_state.get(customer_id)
        if state and state.get("paused", False):
            last_activity = state.get("last_activity", 0)
            elapsed = now - last_activity
            if elapsed < timeout_seconds:
                return True, timeout_seconds - elapsed
            else:
                unpause_bot(customer_id)
                logger.info(f"[Handover] Auto-resumed bot for customer {customer_id} after {elapsed:.0f}s of human inactivity.")
                return False, 0.0

    return False, 0.0


def unpause_bot(customer_id: str) -> None:
    """Bỏ tạm dừng bot cho khách hàng."""
    if customer_id in _handover_state:
        _handover_state[customer_id]["paused"] = False
        _save_state()
        logger.info(f"[Handover] Unpaused bot for customer {customer_id}")


def record_last_customer(customer_id: str) -> None:
    """Lưu lại ID của khách hàng gần nhất vừa chat (chỉ cập nhật memory, không ghi file ngay)."""
    if customer_id:
        _global_state["last_customer_id"] = customer_id


def get_last_customer() -> str:
    """Lấy ID của khách hàng gần nhất vừa chat."""
    return _global_state.get("last_customer_id", "")


def get_handover_status() -> Dict[str, Any]:
    """Trả về báo cáo tình trạng tạm dừng của bot."""
    timeout_seconds = getattr(settings, "HANDOVER_TIMEOUT_HOURS", 2) * 3600
    now = time.time()

    is_global = False
    global_rem = 0.0
    if _global_state.get("paused"):
        elapsed = now - _global_state.get("pause_time", 0.0)
        if elapsed < timeout_seconds:
            is_global = True
            global_rem = timeout_seconds - elapsed

    active_customers = []
    for cid, st in _handover_state.items():
        if st.get("paused"):
            elapsed = now - st.get("last_activity", 0.0)
            if elapsed < timeout_seconds:
                active_customers.append({
                    "customer_id": cid,
                    "remaining_seconds": timeout_seconds - elapsed,
                    "reason": st.get("reason", "")
                })

    return {
        "global_paused": is_global,
        "global_remaining": global_rem,
        "paused_customers_count": len(active_customers),
        "paused_customers": active_customers,
        "last_customer_id": _global_state.get("last_customer_id", "")
    }


def check_human_request_intent(text: str) -> bool:
    """
    Kiểm tra xem câu chat của khách hàng có ý định muốn gặp người thật không.
    Hỗ trợ cả tiếng Việt có dấu và không dấu.
    """
    if not text:
        return False

    text_lower = text.lower().strip()

    keywords = [
        "gặp nhân viên", "gap nhan vien",
        "gặp người thật", "gap nguoi that",
        "chat với người", "chat voi nguoi",
        "nói chuyện với người", "noi chuyen voi nguoi",
        "nói chuyện người thật", "noi chuyen nguoi that",
        "gặp admin", "gap admin",
        "gặp chủ shop", "gap chu shop",
        "chủ shop ơi", "chu shop oi",
        "chủ shop", "chu shop",
        "tư vấn viên", "tu van vien",
        "chuyển nhân viên", "chuyen nhan vien",
        "chuyển người", "chuyen nguoi",
        "gọi người", "goi nguoi",
        "nhân viên đâu", "nhan vien dau",
        "cần người thật", "can nguoi that",
        "cần người hỗ trợ", "can nguoi ho tro",
        "chat với shop", "chat voi shop",
        "người thật đâu", "nguoi that dau",
        "người thật", "nguoi that",
        "gặp shop", "gap shop",
        "người trực page", "nguoi truc page",
        "không nói chuyện với bot", "khong noi chuyen voi bot",
        "đổi người", "doi nguoi",
        "alo shop", "alo shop ơi", "alo shop oi",
        "có ai không", "co ai khong",
        "có ai ko", "co ai ko",
        "có ai trực không", "co ai truc khong",
        "có ai trực ko", "co ai truc ko",
        "shop đâu rồi", "shop dau roi",
        "bot à", "bot a", "bot hả", "bot ha",
        "cho gặp người", "cho gap nguoi"
    ]

    for kw in keywords:
        if kw in text_lower:
            return True

    return False
