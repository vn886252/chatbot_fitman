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


@pytest.mark.asyncio
async def test_send_image_carousel():
    from app.services.facebook_service import send_image_carousel
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message_id": "mid.carousel_789"}
        mock_post.return_value = mock_resp

        images = ["/static/products/mau_moi_1.png", "/static/products/mau_moi_2.png"]
        result = await send_image_carousel("fb_user_999", images)
        assert result is True

        mock_post.assert_called_once()
        call_json = mock_post.call_args[1]["json"]
        assert call_json["message"]["attachment"]["type"] == "template"
        assert call_json["message"]["attachment"]["payload"]["template_type"] == "generic"
        elements = call_json["message"]["attachment"]["payload"]["elements"]
        assert len(elements) == 2
        assert "Mẫu mới 1" in elements[0]["title"]
        assert "Mẫu mới 2" in elements[1]["title"]


def test_tim_anh_san_pham_mau_moi_only_two():
    from app.tools.business_rules import tim_anh_san_pham
    res = tim_anh_san_pham("mẫu mới")
    assert res["found"] is True
    # Chỉ gửi đúng 2 mẫu mới, tuyệt đối không gửi các nhóm cũ
    assert len(res["image_urls"]) == 2
    assert "/static/products/mau_moi_1.png" in res["image_urls"]
    assert "/static/products/mau_moi_2.png" in res["image_urls"]
    assert "/static/products/nhom_1.jpg" not in res["image_urls"]


def test_tim_anh_san_pham_mau_khac():
    from app.tools.business_rules import tim_anh_san_pham
    res = tim_anh_san_pham("mẫu khác")
    assert res["found"] is True
    # Mẫu khác phải có các mẫu cũ
    assert "/static/products/nhom_1.jpg" in res["image_urls"]


def test_tim_anh_san_pham_tat_ca():
    from app.tools.business_rules import tim_anh_san_pham
    res = tim_anh_san_pham("tất cả mẫu")
    assert res["found"] is True
    # Có cả mẫu mới và các mẫu cũ
    assert "/static/products/mau_moi_1.png" in res["image_urls"]
    assert "/static/products/nhom_1.jpg" in res["image_urls"]
    assert "/static/products/nhom_3.jpg" in res["image_urls"]


def test_clean_orphan_bullet_points():
    import re
    raw = "Dạ em gửi bạn xem mẫu mới bên shop nha! 👕\n\n-\n-\n\nBạn xem qua mẫu nào thích thì nhắn em nhé! 💪"
    cleaned = re.sub(r'(?m)^[ \t]*[-*•–—:][ \t]*$', '', raw)
    cleaned = re.sub(r'(?m)^[ \t]+$', '', cleaned)
    cleaned = re.sub(r'\n{2,}', '\n\n', cleaned).strip()
    assert "-\n-" not in cleaned
    assert "-" not in cleaned
    assert cleaned == "Dạ em gửi bạn xem mẫu mới bên shop nha! 👕\n\nBạn xem qua mẫu nào thích thì nhắn em nhé! 💪"


