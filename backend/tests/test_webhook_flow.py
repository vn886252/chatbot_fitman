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

    def test_ping_endpoint(self):
        res = client.get("/ping")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "pong"
        assert "timestamp" in data

    @pytest.mark.anyio
    async def test_webhook_duplicate_mid_is_skipped(self):
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": "10001",
                    "time": 1710000000,
                    "messaging": [
                        {
                            "sender": {"id": "user_psid_retry_test"},
                            "recipient": {"id": "page_id_67890"},
                            "timestamp": 1710000000,
                            "message": {
                                "mid": "mid_unique_retry_999",
                                "text": "Tin nhắn test retry"
                            }
                        }
                    ]
                }
            ]
        }

        with patch("app.routers.webhook.generate_response", new_callable=AsyncMock) as mock_llm, \
             patch("app.routers.webhook.send_text_message", new_callable=AsyncMock) as mock_send_text:

            mock_llm.return_value = {
                "reply_text": "Phản hồi test",
                "tool_calls_made": [],
                "suggested_image": None,
                "updated_messages": []
            }

            # Lần 1: Nhận và xử lý bình thường
            res1 = client.post("/webhook", json=payload)
            assert res1.status_code == 200
            assert mock_llm.await_count == 1
            assert mock_send_text.await_count == 1

            # Lần 2 (Facebook retry cùng mid): Phải bị skip, không gọi LLM hoặc gửi tin lần 2
            res2 = client.post("/webhook", json=payload)
            assert res2.status_code == 200
            assert mock_llm.await_count == 1  # Vẫn là 1, không tăng
            assert mock_send_text.await_count == 1  # Vẫn là 1, không gửi lặp cho khách

    @pytest.mark.anyio
    async def test_webhook_error_message_suppression(self):
        """Kiểm tra nếu hệ thống bận/lỗi nhiều lần liên tiếp thì chỉ gửi 1 thông báo lỗi cho khách."""
        payload = lambda mid_id: {
            "object": "page",
            "entry": [
                {
                    "id": "10001",
                    "time": 1710000000,
                    "messaging": [
                        {
                            "sender": {"id": "user_psid_error_suppress"},
                            "recipient": {"id": "page_id_67890"},
                            "timestamp": 1710000000,
                            "message": {
                                "mid": mid_id,
                                "text": "Câu hỏi lỗi"
                            }
                        }
                    ]
                }
            ]
        }

        with patch("app.routers.webhook.generate_response", new_callable=AsyncMock) as mock_llm, \
             patch("app.routers.webhook.send_text_message", new_callable=AsyncMock) as mock_send_text:

            mock_llm.return_value = {
                "reply_text": "Dạ em chào anh! Hiện tại hệ thống đang bận một chút, anh vui lòng để lại lời nhắn em hỗ trợ ngay nhé ạ!",
                "tool_calls_made": [],
                "suggested_image": None,
                "updated_messages": []
            }

            # Tin nhắn 1 bị lỗi
            res1 = client.post("/webhook", json=payload("mid_err_1"))
            assert res1.status_code == 200
            assert mock_send_text.await_count == 1

            # Tin nhắn 2 cũng bị lỗi trong vòng 60s -> Thông báo bận phải bị chặn, không spam khách
            res2 = client.post("/webhook", json=payload("mid_err_2"))
            assert res2.status_code == 200
            assert mock_send_text.await_count == 1  # Không gửi thêm tin nhắn lỗi thứ 2!

