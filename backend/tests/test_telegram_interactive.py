import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from starlette.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.main import app
from app.services.order_service import get_period_summary
from app.services.telegram_service import (
    format_period_report,
    handle_telegram_update,
    send_period_report,
    send_telegram_menu,
    answer_callback_query,
    REPLY_KEYBOARD,
    INLINE_KEYBOARD
)


def test_get_period_summary_empty():
    """Kiểm tra get_period_summary khi chưa có đơn hàng nào."""
    res_today = get_period_summary("today")
    assert res_today["period_type"] == "today"
    assert "start_date" in res_today
    assert "end_date" in res_today
    assert isinstance(res_today["orders"], list)
    assert res_today["total_orders"] == 0

    res_week = get_period_summary("week")
    assert res_week["period_type"] == "week"
    assert res_week["total_orders"] == 0

    res_month = get_period_summary("month")
    assert res_month["period_type"] == "month"
    assert res_month["total_orders"] == 0


def test_get_period_summary_with_mock_orders():
    """Kiểm tra get_period_summary với danh sách đơn giả lập."""
    mock_orders = [
        {
            "id": "ORD-1",
            "date": "2026-09-18",
            "ten_khach_hang": "Anh Nam",
            "so_luong": 2,
            "tong_tien": 300000,
            "so_dien_thoai": "0912345678"
        },
        {
            "id": "ORD-2",
            "date": "2026-09-18",
            "ten_khach_hang": "Anh Tuấn",
            "so_luong": 3,
            "tong_tien": 400000,
            "so_dien_thoai": "0987654321"
        }
    ]

    with patch("app.services.order_service.ORDERS_FILE") as mock_path, \
         patch("app.services.order_service._get_ict_now") as mock_now, \
         patch("json.load", return_value=mock_orders):
        mock_path.exists.return_value = True
        mock_dt = MagicMock()
        mock_dt.strftime.side_effect = lambda fmt: "2026-09-18" if "%Y-%m-%d" in fmt else "2026-09-01"
        mock_now.return_value = mock_dt

        summary = get_period_summary("today")
        assert summary["total_orders"] == 2
        assert summary["total_items"] == 5
        assert summary["total_revenue"] == 700000
        assert len(summary["orders"]) == 2
        assert "2026-09-18" in summary["daily_breakdown"]
        assert summary["daily_breakdown"]["2026-09-18"]["revenue"] == 700000


def test_format_period_report_today_empty_and_with_orders():
    """Kiểm tra format HTML báo cáo hôm nay khi rỗng và khi có đơn."""
    # Empty
    empty_summary = {
        "period_type": "today",
        "start_date": "2026-09-18",
        "end_date": "2026-09-18",
        "total_orders": 0,
        "total_items": 0,
        "total_revenue": 0,
        "daily_breakdown": {},
        "orders": []
    }
    html_empty = format_period_report(empty_summary)
    assert "BÁO CÁO DOANH THU HÔM NAY" in html_empty
    assert "0" in html_empty
    assert "chưa có đơn hàng nào" in html_empty

    # With orders
    filled_summary = {
        "period_type": "today",
        "start_date": "2026-09-18",
        "end_date": "2026-09-18",
        "total_orders": 1,
        "total_items": 2,
        "total_revenue": 300000,
        "daily_breakdown": {"2026-09-18": {"orders": 1, "items": 2, "revenue": 300000}},
        "orders": [
            {
                "id": "ORD-1",
                "ten_khach_hang": "Anh Nam",
                "so_dien_thoai": "0912345678",
                "so_luong": 2,
                "tong_tien": 300000
            }
        ]
    }
    html_filled = format_period_report(filled_summary)
    assert "300.000đ" in html_filled
    assert "Anh Nam" in html_filled
    assert "0912345678" in html_filled


def test_format_period_report_week_and_month():
    """Kiểm tra format HTML báo cáo 7 ngày và tháng này."""
    week_summary = {
        "period_type": "week",
        "start_date": "2026-09-12",
        "end_date": "2026-09-18",
        "total_orders": 3,
        "total_items": 7,
        "total_revenue": 960000,
        "daily_breakdown": {
            "2026-09-17": {"orders": 1, "items": 2, "revenue": 300000},
            "2026-09-18": {"orders": 2, "items": 5, "revenue": 660000}
        },
        "orders": []
    }
    html_week = format_period_report(week_summary)
    assert "TỔNG KẾT DOANH THU 7 NGÀY QUA" in html_week
    assert "960.000đ" in html_week
    assert "2026-09-17" in html_week
    assert "2026-09-18" in html_week

    month_summary = {
        "period_type": "month",
        "start_date": "2026-09-01",
        "end_date": "2026-09-18",
        "total_orders": 5,
        "total_items": 12,
        "total_revenue": 1600000,
        "daily_breakdown": {
            "2026-09-10": {"orders": 2, "items": 5, "revenue": 640000}
        },
        "orders": []
    }
    html_month = format_period_report(month_summary)
    assert "TỔNG KẾT DOANH THU THÁNG NÀY" in html_month
    assert "1.600.000đ" in html_month


@pytest.mark.asyncio
async def test_handle_telegram_update_unauthorized():
    """Chặn tin nhắn hoặc callback query từ người lạ (khác TELEGRAM_CHAT_ID)."""
    update_msg = {
        "message": {
            "chat": {"id": 999999999},
            "text": "hôm nay"
        }
    }
    res = await handle_telegram_update(update_msg)
    assert res is False

    update_cb = {
        "callback_query": {
            "id": "cb_stranger",
            "data": "report_today",
            "from": {"id": 999999999}
        }
    }
    with patch("app.services.telegram_service.answer_callback_query", new_callable=AsyncMock) as mock_ans:
        res_cb = await handle_telegram_update(update_cb)
        assert res_cb is False
        mock_ans.assert_called_once_with("cb_stranger")


@pytest.mark.asyncio
async def test_handle_telegram_update_text_commands():
    """Xử lý đúng các lệnh tin nhắn từ admin."""
    admin_id = settings.TELEGRAM_CHAT_ID

    with patch("app.services.telegram_service.send_period_report", new_callable=AsyncMock) as mock_report, \
         patch("app.services.telegram_service.send_telegram_menu", new_callable=AsyncMock) as mock_menu:
        mock_report.return_value = True
        mock_menu.return_value = True

        # Test "hôm nay"
        await handle_telegram_update({"message": {"chat": {"id": admin_id}, "text": "hôm nay"}})
        mock_report.assert_called_with(str(admin_id), "today")

        # Test "/today"
        await handle_telegram_update({"message": {"chat": {"id": admin_id}, "text": "/today"}})
        mock_report.assert_called_with(str(admin_id), "today")

        # Test "7 ngày"
        await handle_telegram_update({"message": {"chat": {"id": admin_id}, "text": "7 ngày"}})
        mock_report.assert_called_with(str(admin_id), "week")

        # Test "1 tuần"
        await handle_telegram_update({"message": {"chat": {"id": admin_id}, "text": "1 tuần"}})
        mock_report.assert_called_with(str(admin_id), "week")

        # Test "tháng này"
        await handle_telegram_update({"message": {"chat": {"id": admin_id}, "text": "tháng này"}})
        mock_report.assert_called_with(str(admin_id), "month")

        # Test "/start" -> mở menu
        await handle_telegram_update({"message": {"chat": {"id": admin_id}, "text": "/start"}})
        mock_menu.assert_called_with(str(admin_id))


@pytest.mark.asyncio
async def test_handle_telegram_update_callback_queries():
    """Xử lý đúng khi admin bấm các nút Inline."""
    admin_id = settings.TELEGRAM_CHAT_ID

    with patch("app.services.telegram_service.answer_callback_query", new_callable=AsyncMock) as mock_ans, \
         patch("app.services.telegram_service.send_period_report", new_callable=AsyncMock) as mock_report:
        mock_ans.return_value = True
        mock_report.return_value = True

        # Click "report_today"
        await handle_telegram_update({
            "callback_query": {
                "id": "cb_1",
                "data": "report_today",
                "from": {"id": admin_id}
            }
        })
        mock_ans.assert_called_with("cb_1")
        mock_report.assert_called_with(str(admin_id), "today")

        # Click "report_week"
        await handle_telegram_update({
            "callback_query": {
                "id": "cb_2",
                "data": "report_week",
                "from": {"id": admin_id}
            }
        })
        mock_ans.assert_called_with("cb_2")
        mock_report.assert_called_with(str(admin_id), "week")

        # Click "report_month"
        await handle_telegram_update({
            "callback_query": {
                "id": "cb_3",
                "data": "report_month",
                "from": {"id": admin_id}
            }
        })
        mock_ans.assert_called_with("cb_3")
        mock_report.assert_called_with(str(admin_id), "month")


def test_telegram_webhook_endpoint():
    """Kiểm tra POST /api/telegram/webhook tiếp nhận update thành công."""
    client = TestClient(app)
    admin_id = settings.TELEGRAM_CHAT_ID

    with patch("app.main.handle_telegram_update", new_callable=AsyncMock) as mock_handle:
        mock_handle.return_value = True
        payload = {
            "message": {
                "chat": {"id": admin_id},
                "text": "hôm nay"
            }
        }
        res = client.post("/api/telegram/webhook", json=payload)
        assert res.status_code == 200
        assert res.json() == {"status": "ok", "handled": True}
        mock_handle.assert_called_once()
