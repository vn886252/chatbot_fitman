import os
import re
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

    # Đếm số thứ tự đơn trong ngày (Đơn #1, #2, #3...)
    today_orders = [o for o in orders if o.get("date") == date_str]
    order_number_today = len(today_orders) + 1
    order_id = f"ORD-{now.strftime('%y%m%d')}-{order_number_today:03d}"

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

    # Làm sạch tên khách hàng: chống bịa tên mẫu
    raw_name = str(order_data.get("ten_khach_hang") or "").strip()
    hallucinated_names = [
        "nguyễn văn a", "nguyễn văn tuấn", "trần văn test", "anh nam", 
        "anh tuấn", "anh hùng", "anh minh", "nguyễn văn b", "test", ""
    ]
    if raw_name.lower() in hallucinated_names or not raw_name:
        clean_name = "Khách hàng"
    else:
        clean_name = raw_name

    # Làm sạch địa chỉ: chống bịa địa chỉ mẫu (như 123 Lê Lợi...)
    raw_addr = str(order_data.get("dia_chi") or "").strip()
    hallucinated_addrs = [
        "123 lê lợi", "123 đường lê lợi", "123 abc", "123 đường abc",
        "địa chỉ bạn đã cung cấp", "địa chỉ khách cung cấp", "địa chỉ của anh", ""
    ]
    if raw_addr.lower() in hallucinated_addrs or not raw_addr:
        clean_addr = "Chưa có địa chỉ cụ thể"
    else:
        clean_addr = raw_addr

    # Kiểm tra tính hợp lệ của đơn hàng trước khi tạo
    clean_phone = re.sub(r'\D', '', str(order_data.get("so_dien_thoai") or "")).strip()
    if tong_tien < 100000 or len(clean_phone) < 10 or clean_addr == "Chưa có địa chỉ cụ thể":
        logger.warning(f"Từ chối lưu đơn hàng không hợp lệ: tiền={tong_tien}, SĐT={clean_phone}, địa chỉ={clean_addr}")
        return None

    order = {
        "id": order_id,
        "order_number_today": order_number_today,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": date_str,
        "ten_khach_hang": clean_name,
        "danh_sach_mon": danh_sach_mon,
        "so_luong": so_luong,
        "tong_tien": tong_tien,
        "so_dien_thoai": str(order_data.get("so_dien_thoai") or "").strip(),
        "dia_chi": clean_addr,
        "sender_id": str(order_data.get("sender_id") or "").strip()
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


def get_period_summary(period_type: str = "today") -> dict:
    """
    Tính tổng kết doanh thu và danh sách đơn theo khoảng thời gian:
    - 'today': hôm nay
    - 'week': 7 ngày gần nhất (từ today - 6 ngày đến today)
    - 'month': tháng này (từ ngày 01 đến hôm nay)
    """
    now = _get_ict_now()
    today_str = now.strftime("%Y-%m-%d")

    orders = []
    if ORDERS_FILE.exists():
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f)
        except Exception as e:
            logger.error(f"Error reading orders file: {e}")
            orders = []

    period_type = str(period_type or "today").lower()

    if period_type in ("today", "hom nay", "hôm nay"):
        start_date = today_str
        end_date = today_str
        filtered_orders = [o for o in orders if o.get("date") == today_str]
        normalized_period = "today"
    elif period_type in ("week", "tuan", "tuần", "7 ngày", "1 tuần"):
        start_date = (now - timedelta(days=6)).strftime("%Y-%m-%d")
        end_date = today_str
        filtered_orders = [o for o in orders if start_date <= str(o.get("date", "")) <= end_date]
        normalized_period = "week"
    elif period_type in ("month", "thang", "tháng", "1 tháng", "tháng này"):
        start_date = now.strftime("%Y-%m-01")
        end_date = today_str
        filtered_orders = [o for o in orders if start_date <= str(o.get("date", "")) <= end_date]
        normalized_period = "month"
    else:
        start_date = today_str
        end_date = today_str
        filtered_orders = [o for o in orders if o.get("date") == today_str]
        normalized_period = "today"

    total_orders = len(filtered_orders)
    total_items = sum(o.get("so_luong", 0) for o in filtered_orders)
    total_revenue = sum(o.get("tong_tien", 0) for o in filtered_orders)

    daily_breakdown = {}
    for o in filtered_orders:
        d = str(o.get("date", ""))
        if not d:
            continue
        if d not in daily_breakdown:
            daily_breakdown[d] = {"orders": 0, "revenue": 0, "items": 0}
        daily_breakdown[d]["orders"] += 1
        daily_breakdown[d]["revenue"] += o.get("tong_tien", 0)
        daily_breakdown[d]["items"] += o.get("so_luong", 0)

    sorted_daily_breakdown = dict(sorted(daily_breakdown.items()))

    return {
        "period_type": normalized_period,
        "start_date": start_date,
        "end_date": end_date,
        "total_orders": total_orders,
        "total_items": total_items,
        "total_revenue": total_revenue,
        "daily_breakdown": sorted_daily_breakdown,
        "orders": filtered_orders
    }
