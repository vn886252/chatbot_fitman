import os
import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.facebook_service import send_image_message


@pytest.mark.asyncio
async def test_send_image_message_local_file(tmp_path):
    # Tạo 1 file ảnh giả lập trong tmp_path
    test_img = tmp_path / "model_test.jpg"
    test_img.write_bytes(b"\xff\xd8\xff\xe0test_jpeg_bytes")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message_id": "mid.test_123"}
        mock_post.return_value = mock_resp

        result = await send_image_message("fb_user_999", str(test_img))
        assert result is True

        # Đảm bảo được gọi với data và files (multipart/form-data)
        mock_post.assert_called_once()
        assert "data" in mock_post.call_args[1]
        assert "files" in mock_post.call_args[1]
        assert "filedata" in mock_post.call_args[1]["files"]


@pytest.mark.asyncio
async def test_send_image_message_remote_url():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message_id": "mid.test_456"}
        mock_post.return_value = mock_resp

        result = await send_image_message("fb_user_999", "https://cdn.example.com/photo.jpg")
        assert result is True

        # URL bên ngoài được gửi qua json payload
        mock_post.assert_called_once()
        assert "json" in mock_post.call_args[1]
        assert mock_post.call_args[1]["json"]["message"]["attachment"]["payload"]["url"] == "https://cdn.example.com/photo.jpg"
