import pytest
import sys
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.config import settings

client = TestClient(app)

class TestWebhookAndRoutes:
    """Kiểm thử toàn diện luồng Webhook Facebook & API FastAPI FITMAN"""

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["brand"] == "FITMAN"
        assert data["status"] == "online"

    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_webhook_get_verification_success(self):
        response = client.get(
            f"/webhook?hub.mode=subscribe&hub.verify_token={settings.FB_VERIFY_TOKEN}&hub.challenge=CHALLENGE_CODE_123"
        )
        assert response.status_code == 200
        assert response.text == "CHALLENGE_CODE_123"

    def test_webhook_get_verification_fail_wrong_token(self):
        response = client.get(
            "/webhook?hub.mode=subscribe&hub.verify_token=wrong_token_xyz&hub.challenge=CHALLENGE_CODE_123"
        )
        assert response.status_code == 403

    def test_webhook_get_verification_fail_wrong_mode(self):
        response = client.get(
            f"/webhook?hub.mode=unknown&hub.verify_token={settings.FB_VERIFY_TOKEN}&hub.challenge=CHALLENGE_CODE_123"
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_webhook_post_message_flow(self):
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": "10001",
                    "time": 1710000000,
                    "messaging": [
                        {
                            "sender": {"id": "user_psid_12345"},
                            "recipient": {"id": "page_id_67890"},
                            "timestamp": 1710000000,
                            "message": {
                                "mid": "mid_001",
                                "text": "Tôi cao 1m62 nặng 68kg mặc size gì thế shop?"
                            }
                        }
                    ]
                }
            ]
        }

        with patch("app.routers.webhook.generate_response", new_callable=AsyncMock) as mock_llm, \
             patch("app.routers.webhook.send_text_message", new_callable=AsyncMock) as mock_send_text, \
             patch("app.routers.webhook.send_image_message", new_callable=AsyncMock) as mock_send_img:

            mock_llm.return_value = {
                "reply_text": "Chào gym bro! Với chiều cao 1m62 và nặng 68kg, size chuẩn của bạn là Size L nha.",
                "tool_calls_made": ["tinh_size"],
                "suggested_image": "/static/products/bang_size.jpg",
                "updated_messages": []
            }

            response = client.post("/webhook", json=payload)
            assert response.status_code == 200
            assert response.json() == {"status": "EVENT_RECEIVED"}

            mock_llm.assert_awaited_once_with([], "Tôi cao 1m62 nặng 68kg mặc size gì thế shop?", customer_name="Khách hàng", sender_id="user_psid_12345")
            mock_send_text.assert_awaited_once_with("user_psid_12345", "Chào gym bro! Với chiều cao 1m62 và nặng 68kg, size chuẩn của bạn là Size L nha.")
            mock_send_img.assert_awaited_once_with("user_psid_12345", "/static/products/bang_size.jpg")

    def test_static_files_accessible(self):
        res_bang_size = client.get("/static/products/bang_size.jpg")
        assert res_bang_size.status_code == 200
        assert res_bang_size.headers["content-type"] in ["image/jpeg", "image/jpg"]

        res_nhom1 = client.get("/static/products/nhom_1.jpg")
        assert res_nhom1.status_code == 200
        assert res_nhom1.headers["content-type"] in ["image/jpeg", "image/jpg"]
