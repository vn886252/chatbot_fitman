import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.customer_service import (
    save_customer_profile,
    get_customer_profile,
    format_customer_memory_context
)
from app.services.order_service import save_order


@pytest.fixture
def temp_storage():
    """Tạo file tạm để test, cô lập dữ liệu không ảnh hưởng dữ liệu thật."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as cust_file, \
         tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as order_file:
        cust_path = Path(cust_file.name)
        order_path = Path(order_file.name)

    with patch('app.services.customer_service.CUSTOMERS_FILE', cust_path), \
         patch('app.services.order_service.ORDERS_FILE', order_path):
        yield cust_path, order_path

    if cust_path.exists():
        os.unlink(cust_path)
    if order_path.exists():
        os.unlink(order_path)


def test_save_and_get_customer_profile(temp_storage):
    """Kiểm tra lưu và đọc hồ sơ khách hàng."""
    sender_id = "user_123"
    profile_data = {
        "ten_khach_hang": "Anh Nam",
        "so_dien_thoai": "0794763225",
        "dia_chi": "26 Lê Lợi, Sóc Trăng",
        "chieu_cao": 1.70,
        "can_nang": 72.0,
        "size_ao": "M",
        "size_quan": "L"
    }

    # Lưu hồ sơ
    saved = save_customer_profile(sender_id, profile_data)
    assert saved["sender_id"] == sender_id
    assert saved["ten_khach_hang"] == "Anh Nam"

    # Đọc lại và kiểm tra
    retrieved = get_customer_profile(sender_id)
    assert retrieved is not None
    assert retrieved["ten_khach_hang"] == "Anh Nam"
    assert retrieved["so_dien_thoai"] == "0794763225"
    assert retrieved["dia_chi"] == "26 Lê Lợi, Sóc Trăng"
    assert retrieved["chieu_cao"] == 1.70
    assert retrieved["can_nang"] == 72.0
    assert retrieved["size_ao"] == "M"
    assert retrieved["size_quan"] == "L"

    # Cập nhật số điện thoại mới, các trường cũ vẫn giữ nguyên
    save_customer_profile(sender_id, so_dien_thoai="0912345678")
    updated = get_customer_profile(sender_id)
    assert updated["so_dien_thoai"] == "0912345678"
    assert updated["ten_khach_hang"] == "Anh Nam"
    assert updated["dia_chi"] == "26 Lê Lợi, Sóc Trăng"
    assert updated["size_ao"] == "M"


def test_save_customer_profile_ignores_placeholders(temp_storage):
    """Placeholder như 'Khách hàng' hay 'Chưa có địa chỉ cụ thể' không được ghi đè thông tin thật."""
    sender_id = "user_123"

    # Lưu thông tin thật ban đầu
    save_customer_profile(
        sender_id,
        ten_khach_hang="Anh Nam",
        dia_chi="26 Lê Lợi, Sóc Trăng",
        so_dien_thoai="0794763225"
    )

    # Thử truyền placeholder
    save_customer_profile(
        sender_id,
        ten_khach_hang="Khách hàng",
        dia_chi="Chưa có địa chỉ cụ thể"
    )

    # Đảm bảo không bị ghi đè placeholder
    retrieved = get_customer_profile(sender_id)
    assert retrieved["ten_khach_hang"] == "Anh Nam"
    assert retrieved["dia_chi"] == "26 Lê Lợi, Sóc Trăng"


def test_format_customer_memory_context():
    """Kiểm tra format prompt context cho khách hàng cũ."""
    # Profile rỗng
    assert format_customer_memory_context({}) == ""
    assert format_customer_memory_context(None) == ""

    # Profile có dữ liệu
    profile = {
        "ten_khach_hang": "Anh Nam",
        "so_dien_thoai": "0794763225",
        "dia_chi": "26 Lê Lợi, P6, Sóc Trăng",
        "chieu_cao": 1.70,
        "can_nang": 72.0,
        "size_ao": "M",
        "size_quan": "L"
    }
    context = format_customer_memory_context(profile)
    assert "HỒ SƠ KHÁCH HÀNG CŨ" in context
    assert "26 Lê Lợi, P6, Sóc Trăng" in context
    assert "0794763225" in context
    assert "Cao 1.7m" in context or "1.7" in context
    assert "72" in context
    assert "Áo M" in context
    assert "Quần L" in context
    assert "giao địa chỉ cũ" in context


def test_order_creation_syncs_customer_profile(temp_storage):
    """Tạo đơn hàng thành công tự động cập nhật SĐT và địa chỉ vào hồ sơ khách."""
    sender_id = "user_456"
    order_data = {
        "sender_id": sender_id,
        "ten_khach_hang": "Phan Văn Đức",
        "so_dien_thoai": "0909090909",
        "dia_chi": "100 Nguyễn Huệ, Q1, TP.HCM",
        "danh_sach_mon": ["1 áo 46 size L", "1 quần 1 size L"],
        "so_luong": 2,
        "tong_tien": 300000
    }

    # Tạo đơn hàng
    saved_order = save_order(order_data)
    assert saved_order is not None

    # Kiểm tra hồ sơ khách hàng được tự động lưu
    profile = get_customer_profile(sender_id)
    assert profile is not None
    assert profile["sender_id"] == sender_id
    assert profile["ten_khach_hang"] == "Phan Văn Đức"
    assert profile["so_dien_thoai"] == "0909090909"
    assert profile["dia_chi"] == "100 Nguyễn Huệ, Q1, TP.HCM"
