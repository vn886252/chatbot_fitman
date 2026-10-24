import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tools.business_rules import tinh_size
from app.prompts.system_prompt import get_system_prompt

def test_system_prompt_policies():
    prompt = get_system_prompt()
    # Kiểm tra hàng và đổi size tận nhà
    assert "ĐƯỢC KIỂM TRA HÀNG TRƯỚC KHI NHẬN" in prompt or "kiểm tra hàng" in prompt.lower()
    assert "ĐỔI TẬN NHÀ" in prompt or "đổi tận nhà" in prompt.lower()
    # Không cho mặc thử tại shop / không ghé shop
    assert "KHÔNG BAO GIỜ nói \"ghé shop thử đồ\"" in prompt

def test_system_prompt_size_rules():
    prompt = get_system_prompt()
    # Khách hỏi 100kg
    assert "100kg" in prompt
    assert "DẠ CÓ Ạ" in prompt
    assert "XL" in prompt
    # Khách hỏi áo có size nào
    assert "S, M, L, XL" in prompt
    assert "55kg - 105kg" in prompt
    assert "CẤM nói có size XXL" in prompt or "CẤM NÓI CÓ XXL" in prompt

def test_tinh_size_100kg_xl():
    res = tinh_size(100, None, "áo")
    assert res["size"] == "Áo XL"
    assert "100" in res["ly_do"]

def test_system_prompt_availability_rule():
    prompt = get_system_prompt()
    assert "QUYẾT ĐỊNH 3" in prompt
    assert "LUÔN LUÔN LÀ CÒN HÀNG" in prompt
    assert "TUYỆT ĐỐI CẤM GỌI TOOL `tim_anh_san_pham`" in prompt



def test_system_prompt_initial_two_models_rule():
    prompt = get_system_prompt()
    assert "QUYẾT ĐỊNH 4" in prompt
    assert "CHỈ GỬI ĐÚNG 2 ẢNH MÃ MỚI THÔI" in prompt
    assert "còn mẫu nào nữa shop" in prompt or "thêm mẫu" in prompt

@pytest.mark.asyncio
async def test_price_quote_split():
    from app.services.llm_service import generate_response
    from unittest.mock import patch, MagicMock
    
    mock_llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": (
                    "Dạ bên em đồng giá cả áo và quần, ưu đãi theo combo nha anh:\n"
                    "1 món: 180k (ship 30k)\n"
                    "2 món: 300k freeship\n"
                    "3 món: 400k freeship\n"
                    "Từ món thứ 4 trở đi chỉ 130k/món thôi ạ! 🔥\n\n"
                    "Anh có muốn chọn mẫu nào không ạ?"
                )
            }
        }]
    }
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_llm_response
        mock_post.return_value = mock_resp
        res = await generate_response([], "áo này giá sao shop")
        assert "đồng giá cả áo và quần" in res["reply_text"]
        assert "Anh có muốn chọn mẫu nào không ạ?" not in res["reply_text"]
        assert len(res["suggested_images"]) == 2
        assert res["follow_up_text"] == "Anh đã chọn được mẫu nào chưa ạ? 💪"


@pytest.mark.asyncio
async def test_ask_model_choice_attaches_images_when_not_sent_yet():
    """Khi bot hỏi khách chọn mẫu mà chưa gửi ảnh lần nào -> PHẢI gửi ảnh."""
    from app.services.llm_service import generate_response
    from unittest.mock import patch, MagicMock

    mock_llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "Dạ, bên em miễn phí vận chuyển cho đơn từ 2 món trở lên, còn 1 món thì ship 30k nhé anh! Anh có muốn xem mẫu để chọn thêm món không ạ? 💪"
            }
        }]
    }
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_llm_response
        mock_post.return_value = mock_resp

        res = await generate_response(
            messages=[],
            user_message="Có freeship cho đơn hàng dưới 300k không?",
            sender_id="test_customer_choice_1"
        )
        assert len(res["suggested_images"]) == 2
        assert "Em gửi anh xem 2 mẫu mới nhất bên em nha" in res["reply_text"]


@pytest.mark.asyncio
async def test_ask_model_choice_does_not_attach_images_when_already_sent():
    """Khi bot đã từng gửi ảnh sản phẩm cho khách -> không gửi lặp lại ảnh."""
    from app.services.llm_service import generate_response
    from unittest.mock import patch, MagicMock

    # Giả lập lịch sử đã có tin nhắn gửi mẫu
    history = [
        {"role": "user", "content": "cho xem mẫu"},
        {"role": "assistant", "content": "Em gửi anh xem 2 mẫu mới nhất bên em nha, anh xem qua ưng mẫu nào nhắn em nhé! 💪"}
    ]
    mock_llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "Dạ áo này chất thun lạnh co giãn 4 chiều anh nha! Anh đã chọn được mẫu nào chưa ạ? 💪"
            }
        }]
    }
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_llm_response
        mock_post.return_value = mock_resp

        res = await generate_response(
            messages=history,
            user_message="chất vải gì vậy em",
            sender_id="test_customer_choice_2"
        )
        # Vì đã gửi ảnh trước đó nên không tự động đính kèm thêm ảnh
        assert len(res["suggested_images"]) == 0
        assert "Anh đã chọn được mẫu nào chưa ạ?" in res["reply_text"]

