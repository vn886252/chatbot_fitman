import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

CUSTOMERS_FILE = Path(__file__).parent.parent / "data" / "customers.json"


def _load_customers() -> Dict[str, Dict[str, Any]]:
    """Đọc an toàn danh sách khách hàng từ file JSON."""
    try:
        if not CUSTOMERS_FILE.exists():
            return {}
        with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Error loading customers file: {e}")
        return {}


def _save_customers(customers: Dict[str, Dict[str, Any]]):
    """Ghi danh sách khách hàng vào file JSON."""
    try:
        CUSTOMERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CUSTOMERS_FILE, "w", encoding="utf-8") as f:
            json.dump(customers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving customers file: {e}")


def get_customer_profile(sender_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin hồ sơ của khách hàng theo sender_id."""
    if not sender_id:
        return None
    customers = _load_customers()
    return customers.get(str(sender_id).strip())


def save_customer_profile(sender_id: str, data_dict: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Cập nhật hoặc tạo mới hồ sơ khách hàng theo sender_id.
    Chỉ cập nhật các trường có giá trị thực, bỏ qua placeholder.
    Hỗ trợ truyền dict hoặc kwargs.
    """
    if not sender_id:
        return {}

    merged_data = {}
    if isinstance(data_dict, dict):
        merged_data.update(data_dict)
    merged_data.update(kwargs)

    sid = str(sender_id).strip()
    customers = _load_customers()
    profile = customers.get(sid, {"sender_id": sid})

    valid_fields = [
        "ten_khach_hang",
        "so_dien_thoai",
        "dia_chi",
        "chieu_cao",
        "can_nang",
        "size_ao",
        "size_quan"
    ]

    for field in valid_fields:
        value = merged_data.get(field)
        if value is not None and value != "":
            # Bỏ qua các giá trị placeholder
            if field in ["ten_khach_hang", "dia_chi"]:
                if str(value).strip() in ["Khách hàng", "Chưa có địa chỉ cụ thể", "Chưa có địa chỉ"]:
                    continue
            profile[field] = value

    profile["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    customers[sid] = profile
    _save_customers(customers)
    return profile


def format_customer_memory_context(profile: Optional[Dict[str, Any]]) -> str:
    """
    Chuyển đổi hồ sơ khách hàng thành đoạn chỉ thị rõ ràng cho LLM System Prompt.
    """
    if not profile:
        return ""

    # Kiểm tra xem có ít nhất một thông tin quan trọng (SĐT, địa chỉ, chiều cao, cân nặng)
    has_useful_info = any(
        profile.get(k) for k in ["so_dien_thoai", "dia_chi", "chieu_cao", "can_nang", "size_ao", "size_quan"]
    )
    if not has_useful_info:
        return ""

    lines = []
    if profile.get("ten_khach_hang"):
        lines.append(f"- Tên khách hàng: {profile['ten_khach_hang']}")
    if profile.get("chieu_cao") and profile.get("can_nang"):
        lines.append(f"- Số đo cơ thể đã lưu: Cao {profile['chieu_cao']}m, Nặng {profile['can_nang']}kg")
    elif profile.get("chieu_cao"):
        lines.append(f"- Chiều cao đã lưu: {profile['chieu_cao']}m")
    elif profile.get("can_nang"):
        lines.append(f"- Cân nặng đã lưu: {profile['can_nang']}kg")

    sizes = []
    if profile.get("size_ao"):
        sizes.append(f"Áo {profile['size_ao']}")
    if profile.get("size_quan"):
        sizes.append(f"Quần {profile['size_quan']}")
    if sizes:
        lines.append(f"- Size chuẩn đã tư vấn: {', '.join(sizes)}")

    sdt = profile.get("so_dien_thoai", "")
    dia_chi = profile.get("dia_chi", "")
    if sdt:
        lines.append(f"- Số điện thoại cũ: {sdt}")
    if dia_chi:
        lines.append(f"- Địa chỉ cũ: {dia_chi}")

    info_str = "\n".join(lines)

    context = f"""
=== 👤 HỒ SƠ KHÁCH HÀNG CŨ (HỆ THỐNG ĐÃ GHI NHỚ) ===
{info_str}

QUY TẮC PHỤC VỤ KHÁCH HÀNG CŨ:
1. Nếu khách đã có số đo / size cũ: Không bắt khách khai lại số đo từ đầu. Khi khách chọn mẫu mới, có thể nhắc nhẹ: "Dạ đợt trước anh lấy size {profile.get('size_ao', 'M')} (hoặc Quần {profile.get('size_quan', 'M')}), đợt này anh vẫn lấy size đó đúng không ạ?"
2. Khi khách yêu cầu "giao địa chỉ cũ", "gửi chỗ cũ", "thông tin cũ" HOẶC khi đến bước chốt đơn mà khách không nói địa chỉ mới:
   👉 BẮT BUỘC bạn phải CHỦ ĐỘNG XÁC NHẬN lại thông tin cũ:
   "Dạ đơn này em giao về địa chỉ cũ: {dia_chi}, SĐT: {sdt} đúng không anh?"
3. Khi khách xác nhận đồng ý ("đúng rồi", "ok em", "chuẩn rồi", "giao chỗ cũ đi",...):
   👉 BẠN ĐƯỢC PHÉP GỌI NGAY `tao_don_hang` với so_dien_thoai='{sdt}' và dia_chi='{dia_chi}'! Tuyệt đối KHÔNG bắt khách phải gõ lại địa chỉ hay SĐT!
4. Nếu khách cung cấp địa chỉ hoặc SĐT mới: Sử dụng thông tin mới của khách.
===================================================
"""
    return context.strip()
