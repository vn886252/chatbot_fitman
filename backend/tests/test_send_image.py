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
async def test_send_image_grid():
    from app.services.facebook_service import send_image_grid
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message_id": "mid.grid_123"}
        mock_post.return_value = mock_resp

        images = ["/static/products/mau_moi_1.png", "/static/products/mau_moi_2.png"]
        result = await send_image_grid("fb_user_999", images)
        assert result is True

        mock_post.assert_called_once()
        call_json = mock_post.call_args[1]["json"]
        assert call_json["message"]["attachment"]["type"] == "template"
        assert call_json["message"]["attachment"]["payload"]["template_type"] == "image_grid"
        elements = call_json["message"]["attachment"]["payload"]["elements"]
        assert len(elements[0]["images"]) == 2
        assert "mau_moi_1.png" in elements[0]["images"][0]["url"]
        assert "mau_moi_2.png" in elements[0]["images"][1]["url"]


@pytest.mark.asyncio
async def test_send_image_grid_fallback_attachments():
    from app.services.facebook_service import send_image_grid
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Lần 1: image_grid thất bại (ví dụ 400)
        resp_fail = MagicMock()
        resp_fail.status_code = 400
        resp_fail.text = "Template not supported"

        # Lần 2: attachments array thành công (200)
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {"message_id": "mid.attachments_456"}

        mock_post.side_effect = [resp_fail, resp_ok]

        images = ["/static/products/mau_moi_1.png", "/static/products/mau_moi_2.png"]
        result = await send_image_grid("fb_user_999", images)
        assert result is True

        assert mock_post.call_count == 2
        call2_json = mock_post.call_args_list[1][1]["json"]
        assert "attachments" in call2_json["message"]
        assert len(call2_json["message"]["attachments"]) == 2
        assert "mau_moi_1.png" in call2_json["message"]["attachments"][0]["payload"]["url"]
        assert "mau_moi_2.png" in call2_json["message"]["attachments"][1]["payload"]["url"]



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


def test_clean_verbose_intro():
    import re
    verbose = "Dạ em gửi anh xem các mẫu áo CBUM và Wolves ạ! Anh xem qua ảnh rồi ưng mẫu số mấy nhắn em nhé! Đồng thời anh cho em xin chiều cao và cân nặng để em tư vấn size chuẩn cho mình luôn nha! 👕💪"
    cleaned = re.sub(
        r'(?i)Dạ em gửi (?:anh|chị|bạn) xem các mẫu áo (?:CBUM và Wolves|CBUM|Wolves)\s*ạ!\s*(?:Anh|Chị|Bạn) xem qua ảnh rồi ưng mẫu số mấy nhắn em nhé!\s*Đồng thời (?:anh|chị|bạn) cho em xin chiều cao và cân nặng để em tư vấn size chuẩn cho mình luôn nha!\s*[👕💪]*',
        'Dạ em gửi anh xem mẫu ạ! Anh cho em xin chiều cao và cân nặng để em chọn size chuẩn cho mình nhé! 💪',
        verbose
    )
    assert cleaned == "Dạ em gửi anh xem mẫu ạ! Anh cho em xin chiều cao và cân nặng để em chọn size chuẩn cho mình nhé! 💪"
    assert "CBUM" not in cleaned
    assert "Wolves" not in cleaned





def test_tim_anh_san_pham_mau_ao_only_two():
    from app.tools.business_rules import tim_anh_san_pham
    for q in ["mẫu áo", "cho xem mẫu", "xem mẫu", "gửi mẫu", "có mẫu nào", "áo"]:
        res = tim_anh_san_pham(q)
        assert res["found"] is True
        assert len(res["image_urls"]) == 2
        assert "/static/products/mau_moi_1.png" in res["image_urls"]
        assert "/static/products/mau_moi_2.png" in res["image_urls"]
        assert "/static/products/nhom_1.jpg" not in res["image_urls"]


def test_tim_anh_san_pham_more_models():
    from app.tools.business_rules import tim_anh_san_pham
    for q in ["còn mẫu nào nữa shop", "thêm mẫu", "muốn xem thêm mẫu", "gửi thêm mẫu", "xem thêm mẫu"]:
        res = tim_anh_san_pham(q)
        assert res["found"] is True
        assert "/static/products/nhom_1.jpg" in res["image_urls"]
        assert len(res["image_urls"]) >= 5


@pytest.mark.asyncio
async def test_generate_response_only_two_models_on_initial_query():
    from app.services.llm_service import generate_response
    from unittest.mock import AsyncMock, patch, MagicMock

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Dạ em gửi anh xem 2 mẫu mới nhất bên em nha! Anh cho em xin chiều cao cân nặng để em tư vấn size cho mình nhé! 💪"
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await generate_response([], "cho mình xem mẫu áo với shop")
        assert len(res["suggested_images"]) == 2
        assert "/static/products/mau_moi_1.png" in res["suggested_images"]
        assert "/static/products/mau_moi_2.png" in res["suggested_images"]


@pytest.mark.asyncio
async def test_generate_response_more_models_on_explicit_request():
    from app.services.llm_service import generate_response
    from unittest.mock import AsyncMock, patch, MagicMock

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Dạ em gửi anh xem thêm các mẫu khác bên em nha!"
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await generate_response([], "còn mẫu nào nữa shop ơi")
        assert "/static/products/nhom_1.jpg" in res["suggested_images"]
        assert len(res["suggested_images"]) >= 5
