import os
import sys
import json
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.order_service import save_order, get_daily_summary, get_period_summary
from app.services.telegram_service import format_period_report, send_new_order_notification


@pytest.fixture
def order_data():
    return {
        "sender_id": "user_123",
        "so_dien_thoai": "0912345678",
        "ten_khach_hang": "Khách hàng",
        "danh_sach_mon": ["1 áo 46 size L (170k)", "1 quần Q1 size L (160k)"],
        "so_luong": 2,
        "tong_tien": 300000,
        "dia_chi": "123 Đường Số 1, Phường 2, TP.HCM"
    }


@pytest.fixture
def order_data_updated():
    return {
        "sender_id": "user_123",
        "so_dien_thoai": "0912345678",
        "ten_khach_hang": "Khách hàng",
        "danh_sach_mon": ["1 áo 46", "1 quần Q1", "1 áo 47"],
        "so_luong": 3,
        "tong_tien": 430000,
        "dia_chi": "123 Đường Số 1, Phường 2, TP.HCM"
    }


def test_first_order_creation(tmp_path, order_data):
    orders_file = tmp_path / "orders.json"
    with patch('app.services.order_service.ORDERS_FILE', orders_file):
        result = save_order(order_data)
        assert result["is_updated"] is False
        assert result["order_number_today"] == 1
        assert result["id"].startswith("ORD-")

        assert orders_file.exists()
        with open(orders_file, "r", encoding="utf-8") as f:
            orders = json.load(f)
        assert len(orders) == 1
        assert orders[0]["id"] == result["id"]


def test_modify_or_add_items_updates_existing_order(tmp_path, order_data, order_data_updated):
    orders_file = tmp_path / "orders.json"
    with patch('app.services.order_service.ORDERS_FILE', orders_file):
        # Create first order
        order1 = save_order(order_data)
        assert order1["is_updated"] is False
        assert order1["order_number_today"] == 1

        # Update order with new items and higher quantity/total
        result = save_order(order_data_updated)
        assert result["is_updated"] is True
        assert result["order_number_today"] == 1
        assert result["id"] == order1["id"]
        assert result["so_luong"] == 3
        assert result["tong_tien"] == 430000
        assert len(result["danh_sach_mon"]) == 3

        # Check file has only one order
        with open(orders_file, "r", encoding="utf-8") as f:
            orders = json.load(f)
        assert len(orders) == 1
        assert orders[0]["id"] == order1["id"]
        assert orders[0]["tong_tien"] == 430000

        # Check period summary has 1 order and 430000đ total revenue
        summary = get_period_summary("today")
        assert summary["total_orders"] == 1
        assert summary["total_items"] == 3
        assert summary["total_revenue"] == 430000


def test_different_customer_creates_second_order(tmp_path, order_data):
    orders_file = tmp_path / "orders.json"
    with patch('app.services.order_service.ORDERS_FILE', orders_file):
        # Customer 1
        order_data_1 = order_data.copy()
        order_data_1["sender_id"] = "user_1"
        order_data_1["so_dien_thoai"] = "0912345678"
        save_order(order_data_1)

        # Customer 2
        order_data_2 = order_data.copy()
        order_data_2["sender_id"] = "user_2"
        order_data_2["so_dien_thoai"] = "0987654321"
        result = save_order(order_data_2)

        assert result["is_updated"] is False
        assert result["order_number_today"] == 2

        with open(orders_file, "r", encoding="utf-8") as f:
            orders = json.load(f)
        assert len(orders) == 2


def test_telegram_formatting_clean_phone_and_no_redundancy():
    # Test case 1: No name, phone should be in code tag only, no 'Khách hàng: Khách hàng'
    summary_with_no_name = {
        "period_type": "today",
        "end_date": "2026-09-18",
        "total_orders": 1,
        "total_items": 2,
        "total_revenue": 300000,
        "orders": [
            {
                "ten_khach_hang": "Khách hàng",
                "so_dien_thoai": "0912345678",
                "so_luong": 2,
                "tong_tien": 300000
            }
        ]
    }
    report_text = format_period_report(summary_with_no_name)
    assert "<code>0912345678</code>" in report_text
    assert "(Khách hàng - " not in report_text
    assert "Khách hàng: Khách hàng" not in report_text

    # Test case 2: Has name, should include name and phone
    summary_with_name = {
        "period_type": "today",
        "end_date": "2026-09-18",
        "total_orders": 1,
        "total_items": 1,
        "total_revenue": 170000,
        "orders": [
            {
                "ten_khach_hang": "Phan Văn Đức",
                "so_dien_thoai": "0912345678",
                "so_luong": 1,
                "tong_tien": 170000
            }
        ]
    }
    report_text = format_period_report(summary_with_name)
    assert "(Phan Văn Đức - <code>0912345678</code>)" in report_text


@pytest.mark.asyncio
async def test_send_new_order_notification_formatting():
    with patch("app.services.telegram_service.send_telegram_message") as mock_send:
        mock_send.return_value = True

        # Case A: new order, no real name
        order_new = {
            "id": "ORD-260918-001",
            "order_number_today": 1,
            "ten_khach_hang": "Khách hàng",
            "so_dien_thoai": "0912345678",
            "dia_chi": "123 Lê Lợi",
            "so_luong": 2,
            "tong_tien": 300000,
            "danh_sach_mon": ["Áo 46 size L", "Quần Q1 size L"],
            "is_updated": False
        }
        await send_new_order_notification(order_new)
        msg = mock_send.call_args[0][0]
        assert "🔥 <b>ĐƠN HÀNG MỚI" in msg
        assert "👤 <b>Khách hàng:</b> <code>0912345678</code>" in msg
        assert "Khách hàng: Khách hàng" not in msg

        # Case B: updated order with real name
        order_updated = {
            "id": "ORD-260918-001",
            "order_number_today": 1,
            "ten_khach_hang": "Anh Đức",
            "so_dien_thoai": "0912345678",
            "dia_chi": "123 Lê Lợi",
            "so_luong": 3,
            "tong_tien": 430000,
            "danh_sach_mon": ["Áo 46 size L", "Quần Q1 size L", "Áo 47 size L"],
            "is_updated": True
        }
        await send_new_order_notification(order_updated)
        msg_updated = mock_send.call_args[0][0]
        assert "🔄 <b>ĐƠN HÀNG ĐÃ ĐƯỢC CẬP NHẬT" in msg_updated
        assert "👤 <b>Khách hàng:</b> Anh Đức (<code>0912345678</code>)" in msg_updated
        assert "cập nhật lại chi tiết món và tổng tiền" in msg_updated
