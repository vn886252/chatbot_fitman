import sys
import os
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.handover_service import (
    _handover_state,
    _bot_sent_mids,
    record_bot_sent,
    is_bot_paused
)

client = TestClient(app)


def setup_function():
    _handover_state.clear()
    _bot_sent_mids.clear()


@pytest.mark.asyncio
async def test_webhook_customer_requests_human():
    customer_id = "fb_customer_101"
    payload = {
        "object": "page",
        "entry": [{
            "messaging": [{
                "sender": {"id": customer_id},
                "recipient": {"id": "page_123"},
                "message": {
                    "mid": "mid.cust_001",
                    "text": "cho tôi gặp nhân viên tư vấn với"
                }
            }]
        }]
    }

    with patch("app.routers.webhook.send_handover_alert", new_callable=AsyncMock) as mock_alert, \
         patch("app.routers.webhook.send_text_message", new_callable=AsyncMock) as mock_send:
        mock_alert.return_value = True
        mock_send.return_value = True

        res = client.post("/webhook", json=payload)
        assert res.status_code == 200
        assert res.json() == {"status": "EVENT_RECEIVED"}

        # 1. Bot phải gửi thông báo Telegram cho chủ shop
        mock_alert.assert_called_once()
        call_kwargs = mock_alert.call_args[1]
        assert call_kwargs["customer_id"] == customer_id
        assert call_kwargs["event_type"] == "customer_requested"

        # 2. Bot phải nhắn khách câu thông báo chờ nhân viên
        mock_send.assert_called_once()
        assert "nhân viên" in mock_send.call_args[0][1]

        # 3. Trạng thái khách phải chuyển sang paused
        paused, remaining = is_bot_paused(customer_id)
        assert paused is True
        assert remaining > 7100


@pytest.mark.asyncio
async def test_webhook_bot_stays_silent_when_paused():
    customer_id = "fb_customer_102"
    # Giả sử khách đã bị pause
    _handover_state[customer_id] = {
        "paused": True,
        "last_activity": 1000000000.0,
        "reason": "customer_requested"
    }
    # Set last_activity là gần đây (vừa mới pause)
    import time
    _handover_state[customer_id]["last_activity"] = time.time()

    payload = {
        "object": "page",
        "entry": [{
            "messaging": [{
                "sender": {"id": customer_id},
                "recipient": {"id": "page_123"},
                "message": {
                    "mid": "mid.cust_002",
                    "text": "alo shop ơi giá sao"
                }
            }]
        }]
    }

    with patch("app.routers.webhook.generate_response", new_callable=AsyncMock) as mock_llm, \
         patch("app.routers.webhook.send_text_message", new_callable=AsyncMock) as mock_send:

        res = client.post("/webhook", json=payload)
        assert res.status_code == 200

        # LLM và send_text_message tuyệt đối KHÔNG được gọi vì bot đang im lặng
        mock_llm.assert_not_called()
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_human_echo_pauses_bot_and_alerts():
    customer_id = "fb_customer_103"
    payload = {
        "object": "page",
        "entry": [{
            "messaging": [{
                "sender": {"id": "page_123"},
                "recipient": {"id": customer_id},
                "message": {
                    "is_echo": True,
                    "mid": "mid.human_page_inbox_001",
                    "text": "Chào anh, em là nhân viên Fitman đây ạ!"
                }
            }]
        }]
    }

    with patch("app.routers.webhook.send_handover_alert", new_callable=AsyncMock) as mock_alert:
        mock_alert.return_value = True

        res = client.post("/webhook", json=payload)
        assert res.status_code == 200

        # Bot nhận diện người thật nhắn từ Inbox -> gửi Telegram alert
        mock_alert.assert_called_once()
        assert mock_alert.call_args[1]["event_type"] == "human_chatting"
        assert mock_alert.call_args[1]["customer_id"] == customer_id

        # Trạng thái bot với khách chuyển thành paused
        paused, _ = is_bot_paused(customer_id)
        assert paused is True


@pytest.mark.asyncio
async def test_webhook_bot_own_echo_is_ignored():
    customer_id = "fb_customer_104"
    bot_mid = "mid.bot_sent_001"
    record_bot_sent(bot_mid)

    payload = {
        "object": "page",
        "entry": [{
            "messaging": [{
                "sender": {"id": "page_123"},
                "recipient": {"id": customer_id},
                "message": {
                    "is_echo": True,
                    "mid": bot_mid,
                    "text": "Dạ đơn của anh là..."
                }
            }]
        }]
    }

    with patch("app.routers.webhook.send_handover_alert", new_callable=AsyncMock) as mock_alert:
        res = client.post("/webhook", json=payload)
        assert res.status_code == 200

        # Vì là echo từ chính bot gửi -> không gửi alert, không pause người thật
        mock_alert.assert_not_called()
