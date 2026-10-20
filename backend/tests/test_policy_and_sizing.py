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

