import os
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# File lưu đơn hàng tại backend/app/data/orders.json
ORDERS_FILE = Path(__file__).parent.parent / "data" / "orders.json"
ICT = timezone(timedelta(hours=7))


def _get_ict_now() -> datetime:
    """Lấy thời gian hiện tại theo múi giờ Việt Nam (UTC+7)."""
    return datetime.now(timezone.utc).astimezone(ICT)


def save_order(order_data: dict) -> dict:
    """
    Lưu đơn hàng mới vào file orders.json.
    order_data gồm:
      - ten_khach_hang: str
      - danh_sach_mon: list[str] hoặc str
      - so_luong: int
      - tong_tien: int
      - so_dien_thoai: str
      - dia_chi: str
      - sender_id: Optional[str]
    """
    ORDERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    orders = []
    if ORDERS_FILE.exists():
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f)
        except Exception as e:
            logger.error(f"Error reading orders file: {e}")
            orders = []

    now = _get_ict_now()
    date_str = now.strftime("%Y-%m-%d")
    order_id = f"ORD-{now.strftime('%y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

    danh_sach_mon = order_data.get("danh_sach_mon", [])
    if isinstance(danh_sach_mon, str):
        danh_sach_mon = [danh_sach_mon]

    try:
        so_luong = int(order_data.get("so_luong", len(danh_sach_mon) or 1))
    except Exception:
        so_luong = len(danh_sach_mon) or 1

    try:
        tong_tien = int(order_data.get("tong_tien", 0))
    except Exception:
        tong_tien = 0

    order = {
        "id": order_id,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": date_str,
        "ten_khach_hang": str(order_data.get("ten_khach_hang") or "Khách hàng"),
        "danh_sach_mon": danh_sach_mon,
        "so_luong": so_luong,
        "tong_tien": tong_tien,
        "so_dien_thoai": str(order_data.get("so_dien_thoai") or ""),
        "dia_chi": str(order_data.get("dia_chi") or ""),
        "sender_id": str(order_data.get("sender_id") or "")
    }

    orders.append(order)

    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
        logger.info(f"Order saved successfully: {order_id} for {order['ten_khach_hang']}")
    except Exception as e:
        logger.error(f"Error writing orders file: {e}")

    return order


def get_daily_summary(target_date: Optional[str] = None) -> dict:
    """
    Tính tổng kết doanh thu và danh sách đơn theo ngày (mặc định hôm nay ICT).
    """
    if not target_date:
        now = _get_ict_now()
        target_date = now.strftime("%Y-%m-%d")

    orders = []
    if ORDERS_FILE.exists():
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f)
        except Exception as e:
            logger.error(f"Error reading orders file: {e}")
            orders = []

    daily_orders = [o for o in orders if o.get("date") == target_date]

    total_items = sum(o.get("so_luong", 0) for o in daily_orders)
    total_revenue = sum(o.get("tong_tien", 0) for o in daily_orders)
    total_orders = len(daily_orders)

    return {
        "date": target_date,
        "total_orders": total_orders,
        "total_items": total_items,
        "total_revenue": total_revenue,
        "orders": daily_orders
    }
