import sys
import os
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.handover_service import _handover_state, is_bot_paused
from app.services.telegram_service import send_handover_alert, send_telegram_photo

client = TestClient(app)


def setup_function():
    _handover_state.clear()


@pytest.mark.asyncio
async def test_webhook_customer_sends_image_only():
    customer_id = "fb_customer_img_01"
    image_url = "https://cdn.fbsbx.com/v/t59/test_shirt.jpg"
    payload = {
        "object": "page",
        "entry": [{
            "messaging": [{
                "sender": {"id": customer_id},
                "recipient": {"id": "page_123"},
                "message": {
                    "mid": "mid.cust_img_001",
                    "attachments": [
                        {
                            "type": "image",
                            "payload": {"url": image_url}
                        }
                    ]
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

        # 1. Báo Telegram kèm URL ảnh
        mock_alert.assert_called_once()
        call_kwargs = mock_alert.call_args[1]
        assert call_kwargs["customer_id"] == customer_id
        assert call_kwargs["event_type"] == "customer_sent_image"
        assert call_kwargs["image_url"] == image_url

        # 2. Phản hồi cho khách trên Messenger
        mock_send.assert_called_once()
        reply_sent = mock_send.call_args[0][1]
        assert "nhận được ảnh mẫu" in reply_sent
        assert "chiều cao" in reply_sent


@pytest.mark.asyncio
async def test_webhook_customer_sends_image_with_caption():
    customer_id = "fb_customer_img_02"
    image_url = "https://cdn.fbsbx.com/v/t59/test_shirt_2.jpg"
    payload = {
        "object": "page",
        "entry": [{
            "messaging": [{
                "sender": {"id": customer_id},
                "recipient": {"id": "page_123"},
                "message": {
                    "mid": "mid.cust_img_002",
                    "text": "áo này còn size L không shop ơi",
                    "attachments": [
                        {
                            "type": "image",
                            "payload": {"url": image_url}
                        }
                    ]
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

        mock_alert.assert_called_once()
        call_kwargs = mock_alert.call_args[1]
        assert call_kwargs["user_text"] == "áo này còn size L không shop ơi"
        assert call_kwargs["image_url"] == image_url

        mock_send.assert_called_once()
        reply_sent = mock_send.call_args[0][1]
        assert "nhận được ảnh mẫu" in reply_sent


@pytest.mark.asyncio
async def test_webhook_customer_sends_image_when_bot_paused():
    customer_id = "fb_customer_img_03"
    import time
    _handover_state[customer_id] = {
        "paused": True,
        "last_activity": time.time(),
        "reason": "human_chatting"
    }

    payload = {
        "object": "page",
        "entry": [{
            "messaging": [{
                "sender": {"id": customer_id},
                "recipient": {"id": "page_123"},
                "message": {
                    "mid": "mid.cust_img_003",
                    "attachments": [{"type": "image", "payload": {"url": "https://cdn.com/1.jpg"}}]
                }
            }]
        }]
    }

    with patch("app.routers.webhook.send_handover_alert", new_callable=AsyncMock) as mock_alert, \
         patch("app.routers.webhook.send_text_message", new_callable=AsyncMock) as mock_send:

        res = client.post("/webhook", json=payload)
        assert res.status_code == 200

        # Khi bot đang paused (người thật chat), bot im lặng hoàn toàn
        mock_alert.assert_not_called()
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_send_handover_alert_image_telegram():
    with patch("app.services.telegram_service.send_telegram_photo", new_callable=AsyncMock) as mock_photo, \
         patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_msg:

        mock_photo.return_value = True

        # Khi có image_url, ưu tiên gửi photo
        success = await send_handover_alert(
            customer_id="cust_888",
            customer_name="Trần Văn B",
            event_type="customer_sent_image",
            user_text="Mẫu này còn k",
            image_url="https://test.com/photo.jpg"
        )
        assert success is True
        mock_photo.assert_called_once()
        assert mock_photo.call_args[0][0] == "https://test.com/photo.jpg"
        assert "Trần Văn B" in mock_photo.call_args[1]["caption"]
        mock_msg.assert_not_called()

        # Nếu gửi photo lỗi -> fallback sang text message bình thường
        mock_photo.reset_mock()
        mock_photo.return_value = False
        mock_msg.return_value = True

        success_fallback = await send_handover_alert(
            customer_id="cust_888",
            customer_name="Trần Văn B",
            event_type="customer_sent_image",
            user_text="Mẫu này còn k",
            image_url="https://test.com/photo.jpg"
        )
        assert success_fallback is True
        mock_photo.assert_called_once()
        mock_msg.assert_called_once()
        assert "Trần Văn B" in mock_msg.call_args[0][0]


@pytest.mark.asyncio
async def test_handover_alert_includes_fanpage_chat_link(tmp_path):
    """Kiểm tra thông báo handover có nút mở chat Fanpage và thông tin định danh khách hàng."""
    from app.services.telegram_service import send_handover_alert
    from app.services.customer_service import save_customer_profile

    customers_file = tmp_path / "test_link_customers.json"
    with patch("app.services.customer_service.CUSTOMERS_FILE", customers_file), \
         patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send:

        mock_send.return_value = True

        save_customer_profile(
            "fb_psid_999",
            ten_khach_hang="Nguyễn Văn Hùng",
            so_dien_thoai="0911223344",
            chieu_cao="175",
            can_nang="75",
            size_ao="L",
            ad_campaign_name="Áo Basketball Fitman",
            ad_post_id="1523979186418810"
        )

        success = await send_handover_alert(
            customer_id="fb_psid_999",
            customer_name="Khách hàng",
            event_type="customer_requested",
            user_text="Em muốn hỏi thêm về size"
        )
        assert success is True
        mock_send.assert_called_once()
        msg_text = mock_send.call_args[0][0]
        reply_markup = mock_send.call_args[1].get("reply_markup") or {}

        # Kiểm tra nội dung tin nhắn được bổ sung đầy đủ thông tin định danh
        assert "Nguyễn Văn Hùng" in msg_text
        assert "0911223344" in msg_text
        assert "175cm, 75kg, Size L" in msg_text
        assert "Áo Basketball Fitman" in msg_text
        assert "1523979186418810" in msg_text

        # Kiểm tra nút bấm mở chat Fanpage
        inline_kb = reply_markup.get("inline_keyboard", [])
        assert len(inline_kb) >= 1
        first_btn = inline_kb[0][0]
        assert first_btn["text"] == "💬 Mở chat trên Fanpage"
        assert "business.facebook.com/latest/inbox/messenger?selected_item_id=fb_psid_999" in first_btn["url"]

