import pytest
import sys
import os
import httpx

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.llm_service import generate_response
from app.config import settings

def is_local_qwen_running() -> bool:
    try:
        resp = httpx.get(f"{settings.QWEN_API_BASE.rstrip('/')}/models", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False

@pytest.mark.skipif(not is_local_qwen_running(), reason="Qwen 3 Coder local server is not running on port 5001")
@pytest.mark.anyio
class TestLLMToolCallingLive:
    """Kiểm thử thực tế với LLM Qwen 3 Coder đang chạy trên port 5001"""

    async def test_live_tool_calling_tinh_size(self):
        user_msg = "Tôi cao 1m62 nặng 68kg mặc size gì thế shop?"
        result = await generate_response([], user_msg)
        
        assert "tinh_size" in result["tool_calls_made"]
        assert result["suggested_image"] == "/static/products/bang_size.jpg"
        assert len(result["reply_text"]) > 0
        reply_lower = result["reply_text"].lower()
        assert "l" in reply_lower or "size l" in reply_lower

    async def test_live_tool_calling_tinh_gia_with_polite_greeting(self):
        user_msg = "Mình lấy 2 áo với 2 quần thì hết bao nhiêu tiền?"
        result = await generate_response([], user_msg)

        assert "tinh_gia" in result["tool_calls_made"]
        reply = result["reply_text"].lower()
        assert ("530" in reply) or ("530.000" in reply) or ("freeship" in reply)
        assert any(term in reply for term in ["dạ", "anh", "bác", "gym bro", "shop", "em"])

    async def test_live_image_suggestion_by_product_code(self):
        # Test mã quần Q1 -> nhom_3.jpg
        res_q1 = await generate_response([], "Cho mình xem mẫu quần mã Q1 với shop")
        assert res_q1["suggested_image"] == "/static/products/nhom_3.jpg"

        # Test mã áo W1 -> nhom_4.jpg
        res_w1 = await generate_response([], "Shop gửi ảnh mẫu áo W1 giúp mình")
        assert res_w1["suggested_image"] == "/static/products/nhom_4.jpg"

    async def test_live_view_all_pants_images(self):
        # Test "xem ảnh quần" -> gửi cả nhom_3.jpg và nhom_5.jpg
        res = await generate_response([], "xem ảnh quần")
        assert len(res["suggested_images"]) >= 2
        assert "/static/products/nhom_3.jpg" in res["suggested_images"]
        assert "/static/products/nhom_5.jpg" in res["suggested_images"]

    async def test_live_order_confirmation(self):
        user_msg = "Mình chốt lấy 2 áo 1 quần size L nhé. Ship tới 26 Lê Lợi P6 Sóc Trăng, SĐT 0794763225 nha shop"
        result = await generate_response([], user_msg)

        reply = result["reply_text"].lower()
        assert "0794763225" in reply or "sdt" in reply or "sđt" in reply
        assert "lê lợi" in reply or "sóc trăng" in reply
        assert "cảm ơn" in reply or "cam on" in reply
