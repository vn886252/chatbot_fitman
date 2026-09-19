import os
import sys
import json
import pytest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import new_models_service
from app.tools.business_rules import tim_anh_san_pham, ALL_ANH_AO, ALL_ANH_QUAN
from app.services.telegram_service import handle_telegram_update
from app.config import settings

@pytest.fixture(autouse=True)
def clean_new_models(tmp_path, monkeypatch):
    """Sử dụng file new_models.json tạm thời trong quá trình chạy test."""
    temp_file = tmp_path / "new_models.json"
    temp_file.write_text(json.dumps({"max_display": 6, "models": []}), encoding="utf-8")
    monkeypatch.setattr(new_models_service, "_get_data_path", lambda: str(temp_file))
    yield temp_file


def test_parse_model_caption():
    """Kiểm tra parser tách mã mẫu và mô tả từ caption chủ shop nhập."""
    # Chỉ nhập mã số
    code, desc = new_models_service.parse_model_caption("48")
    assert code == "48"
    assert desc == "Mẫu 48"

    # Nhập mã số kèm mô tả
    code, desc = new_models_service.parse_model_caption("48 Áo CBUM Olympia đen")
    assert code == "48"
    assert desc == "Áo CBUM Olympia đen"

    # Nhập tiền tố mã/mẫu
    code, desc = new_models_service.parse_model_caption("mã 49: Áo thun trắng")
    assert code == "49"
    assert desc == "Áo thun trắng"

    # Nhập mã chữ như W8, Q8
    code, desc = new_models_service.parse_model_caption("W8 Áo Wolves punk")
    assert code == "W8"
    assert desc == "Áo Wolves punk"

    code, desc = new_models_service.parse_model_caption("Q8 Quần đùi CBUM")
    assert code == "Q8"
    assert desc == "Quần đùi CBUM"

    # Caption rỗng hoặc từ chung chung -> trả về None
    assert new_models_service.parse_model_caption("")[0] is None
    assert new_models_service.parse_model_caption("thêm mẫu")[0] is None
    assert new_models_service.parse_model_caption("mẫu mới")[0] is None


def test_add_and_sliding_window_custom_codes():
    """Kiểm tra cơ chế sliding window với mã mẫu tự đặt: thêm 1-6 gửi 1-6, thêm 7-8 gửi 3-8."""
    # Thêm 6 mẫu đầu tiên với mã do chủ shop đặt (ví dụ: M1 đến M6)
    for i in range(1, 7):
        new_models_service.add_new_model(
            f"/static/products/new_models/model_M{i}.jpg",
            model_id=f"M{i}",
            description=f"Mẫu M{i}"
        )

    new_m = new_models_service.get_new_models()
    old_m = new_models_service.get_old_models()
    assert len(new_m) == 6
    assert [m["id"] for m in new_m] == ["M1", "M2", "M3", "M4", "M5", "M6"]
    assert old_m == []

    # Thêm mẫu M7 và M8
    new_models_service.add_new_model("/static/products/new_models/model_M7.jpg", model_id="M7", description="Mẫu M7")
    new_models_service.add_new_model("/static/products/new_models/model_M8.jpg", model_id="M8", description="Mẫu M8")

    new_m2 = new_models_service.get_new_models()
    old_m2 = new_models_service.get_old_models()

    # 6 mẫu mới nhất hiển thị: M3 -> M8
    assert len(new_m2) == 6
    assert [m["id"] for m in new_m2] == ["M3", "M4", "M5", "M6", "M7", "M8"]

    # Mẫu cũ bị đẩy ra: M1, M2
    assert len(old_m2) == 2
    assert [m["id"] for m in old_m2] == ["M1", "M2"]


def test_remove_model():
    """Kiểm tra xóa mẫu theo mã tự đặt."""
    new_models_service.add_new_model("/static/products/new_models/model_48.jpg", model_id="48", description="Áo 48")
    new_models_service.add_new_model("/static/products/new_models/model_49.jpg", model_id="49", description="Áo 49")

    assert new_models_service.remove_model("48") is True
    assert new_models_service.remove_model("999") is False

    remaining = new_models_service.get_new_models()
    assert len(remaining) == 1
    assert remaining[0]["id"] == "49"


def test_tim_anh_san_pham_custom_codes():
    """Kiểm tra tim_anh_san_pham tra cứu mã do chủ shop tự đặt (ví dụ: 48, W8, Q8)."""
    # Thêm mẫu 48 và W8
    new_models_service.add_new_model("/static/products/new_models/model_48.jpg", model_id="48", description="Áo 48")
    new_models_service.add_new_model("/static/products/new_models/model_W8.jpg", model_id="W8", description="Áo W8")

    # Tra cứu trực tiếp mã "48"
    res_48 = tim_anh_san_pham("48")
    assert res_48["image_urls"] == ["/static/products/new_models/model_48.jpg"]

    # Tra cứu trong câu chat "cho xem áo 48"
    res_chat = tim_anh_san_pham("cho xem áo 48")
    assert res_chat["image_urls"] == ["/static/products/new_models/model_48.jpg"]

    # Tra cứu mã "W8"
    res_w8 = tim_anh_san_pham("W8")
    assert res_w8["image_urls"] == ["/static/products/new_models/model_W8.jpg"]


@pytest.mark.asyncio
async def test_telegram_custom_code_management():
    """Kiểm tra upload ảnh có mã, thiếu mã và lệnh xóa mã trên Telegram."""
    chat_id = settings.TELEGRAM_CHAT_ID

    # 1. Gửi ảnh KHÔNG có mã -> Bot nhắc nhở thiếu mã
    with patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        photo_no_code = {
            "message": {
                "chat": {"id": chat_id},
                "photo": [{"file_id": "large_photo"}],
                "caption": ""
            }
        }
        res = await handle_telegram_update(photo_no_code)
        assert res is True
        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][0]
        assert "THIẾU MÃ MẪU" in sent_text

    # 2. Gửi ảnh CÓ mã chủ shop tự đặt "48 Áo CBUM đen"
    with patch("app.services.new_models_service.download_telegram_photo", new_callable=AsyncMock) as mock_download:
        mock_download.return_value = "/static/products/new_models/model_48.jpg"
        with patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            photo_with_code = {
                "message": {
                    "chat": {"id": chat_id},
                    "photo": [{"file_id": "large_photo_48"}],
                    "caption": "48 Áo CBUM đen"
                }
            }
            res = await handle_telegram_update(photo_with_code)
            assert res is True
            mock_download.assert_called_once_with("large_photo_48", model_id="48")
            mock_send.assert_called_once()
            sent_text = mock_send.call_args[0][0]
            assert "ĐÃ LƯU MẪU 48 THÀNH CÔNG" in sent_text

    # 3. Xóa mẫu 48
    with patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        del_update = {
            "message": {
                "chat": {"id": chat_id},
                "text": "/xoa_mau 48"
            }
        }
        res = await handle_telegram_update(del_update)
        assert res is True
        mock_send.assert_called_once()
        assert "Đã xóa mẫu <code>48</code> thành công" in mock_send.call_args[0][0]
