import pytest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import AsyncMock, patch
from app.services.handover_service import (
    record_bot_sent,
    is_bot_sent,
    pause_bot,
    unpause_bot,
    is_bot_paused,
    record_human_message,
    check_human_request_intent,
    _handover_state,
    _bot_sent_mids
)
from app.services.telegram_service import send_handover_alert


def setup_function():
    """Reset handover state before each test."""
    _handover_state.clear()
    _bot_sent_mids.clear()


def test_bot_sent_mids_cache():
    # Ban đầu mid chưa có
    assert not is_bot_sent("mid.12345")

    # Ghi nhận bot gửi
    record_bot_sent("mid.12345")
    assert is_bot_sent("mid.12345")
    assert not is_bot_sent("mid.other")


def test_check_human_request_intent():
    # Các câu yêu cầu gặp người thật
    positive_cases = [
        "cho tôi gặp nhân viên",
        "gặp người thật đi",
        "chat voi nguoi",
        "tôi muốn gặp chủ shop",
        "chuyển nhân viên giúp mình",
        "gọi người thật ra nói chuyện",
        "nhân viên đâu rồi",
        "cần người thật tư vấn",
        "không nói chuyện với bot nữa"
    ]
    for text in positive_cases:
        assert check_human_request_intent(text) is True, f"Failed on: {text}"

    # Các câu chat thông thường
    negative_cases = [
        "cho xem mẫu áo 1",
        "mẫu mới giá sao shop",
        "mình cao 1m7 nặng 70kg",
        "size L có vừa không",
        "ship về 123 Lê Lợi nha"
    ]
    for text in negative_cases:
        assert check_human_request_intent(text) is False, f"False positive on: {text}"


def test_pause_and_auto_resume():
    customer_id = "user_test_999"

    # Ban đầu không bị pause
    paused, _ = is_bot_paused(customer_id)
    assert not paused

    # Pause bot
    pause_bot(customer_id, reason="customer_requested")
    paused, remaining = is_bot_paused(customer_id)
    assert paused is True
    assert remaining > 7100  # Gần 7200 giây (2 giờ)

    # Giả lập thời gian trôi qua 1 giờ (3600s) -> Vẫn pause
    _handover_state[customer_id]["last_activity"] -= 3600
    paused, remaining = is_bot_paused(customer_id)
    assert paused is True
    assert 3500 < remaining < 3610

    # Giả lập thời gian trôi qua hơn 2 giờ (7250s) -> Tự động bật lại (unpause)
    _handover_state[customer_id]["last_activity"] -= 3700
    paused, remaining = is_bot_paused(customer_id)
    assert paused is False
    assert remaining == 0.0


def test_record_human_message_extends_timeout():
    customer_id = "user_test_888"

    # Người thật gửi tin nhắn đầu tiên
    is_first = record_human_message(customer_id)
    assert is_first is True
    paused, remaining = is_bot_paused(customer_id)
    assert paused is True

    # Giả lập trôi qua 1 tiếng
    _handover_state[customer_id]["last_activity"] -= 3600

    # Người thật gửi tin nhắn tiếp theo trong phiên
    is_second = record_human_message(customer_id)
    assert is_second is False  # Không báo lặp lại telegram
    paused, remaining = is_bot_paused(customer_id)
    assert paused is True
    # Timeout được reset lại đủ 2 giờ kể từ tin nhắn mới này
    assert remaining > 7100


@pytest.mark.asyncio
async def test_send_handover_alert_telegram():
    with patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        # Test customer requested
        success = await send_handover_alert("user_123", "Nguyễn Văn A", "customer_requested", "tôi muốn gặp nhân viên")
        assert success is True
        mock_send.assert_called_once()
        msg_text = mock_send.call_args[0][0]
        assert "YÊU CẦU GẶP NGƯỜI THẬT" in msg_text
        assert "Nguyễn Văn A" in msg_text
        assert "tôi muốn gặp nhân viên" in msg_text

        # Test human chatting
        mock_send.reset_mock()
        success2 = await send_handover_alert("user_123", "Nguyễn Văn A", "human_chatting", "Chào bạn, shop hỗ trợ gì ạ")
        assert success2 is True
        msg_text2 = mock_send.call_args[0][0]
        assert "NHÂN VIÊN ĐANG CHAT VỚI KHÁCH" in msg_text2


def test_global_pause_and_resume():
    from app.services.handover_service import pause_global, unpause_global, unpause_all, is_bot_paused, get_handover_status
    # Tạm dừng toàn bộ bot
    timeout_h = pause_global("test")
    assert timeout_h == 2.0
    status = get_handover_status()
    assert status["global_paused"] is True
    assert status["global_remaining"] > 7100

    # Mọi khách hàng đều bị pause khi global_paused = True
    paused, rem = is_bot_paused("random_customer_1")
    assert paused is True
    assert rem > 7100

    paused2, rem2 = is_bot_paused("random_customer_2")
    assert paused2 is True

    # Bật lại toàn bộ
    unpause_all()
    assert is_bot_paused("random_customer_1")[0] is False
    assert get_handover_status()["global_paused"] is False


def test_handover_persistence_file(tmp_path, monkeypatch):
    import app.services.handover_service as hs
    temp_file = tmp_path / "handover.json"
    monkeypatch.setattr(hs, "_get_data_path", lambda: str(temp_file))

    # Tạm dừng khách hàng
    hs.pause_bot("customer_persistent_01", reason="test")
    assert temp_file.exists()

    # Xóa RAM
    hs._handover_state.clear()
    assert "customer_persistent_01" not in hs._handover_state

    # Tải lại từ file
    hs._load_state()
    assert "customer_persistent_01" in hs._handover_state
    paused, _ = hs.is_bot_paused("customer_persistent_01")
    assert paused is True


@pytest.mark.asyncio
async def test_telegram_pause_resume_commands():
    from app.services.telegram_service import handle_telegram_update
    from app.services.handover_service import is_bot_paused, unpause_all
    from app.config import settings

    chat_id = settings.TELEGRAM_CHAT_ID

    # 1. Bấm nút Tạm dừng Bot (Toàn bộ)
    with patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        update = {
            "message": {
                "chat": {"id": chat_id},
                "text": "⏸️ Tạm dừng Bot"
            }
        }
        res = await handle_telegram_update(update)
        assert res is True
        mock_send.assert_called_once()
        assert "ĐÃ TẠM DỪNG TOÀN BỘ BOT" in mock_send.call_args[0][0]
        assert is_bot_paused("any_user")[0] is True

    # 2. Bấm nút Bật lại Bot
    with patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        update_resume = {
            "message": {
                "chat": {"id": chat_id},
                "text": "▶️ Bật lại Bot"
            }
        }
        res = await handle_telegram_update(update_resume)
        assert res is True
        mock_send.assert_called_once()
        assert "ĐÃ BẬT LẠI BOT" in mock_send.call_args[0][0]
        assert is_bot_paused("any_user")[0] is False

    # 3. Click nút inline "pause_user_cust123"
    with patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        cb_update = {
            "callback_query": {
                "id": "cb_001",
                "from": {"id": chat_id},
                "data": "pause_user_cust123"
            }
        }
        res = await handle_telegram_update(cb_update)
        assert res is True
        mock_send.assert_called_once()
        assert "cust123" in mock_send.call_args[0][0]
        assert is_bot_paused("cust123")[0] is True

