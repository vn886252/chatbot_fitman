import re
from typing import Dict, List, Union, Optional, Any

# Danh mục nhóm sản phẩm & bảng size chuẩn theo hệ thống Fitman
DANH_MUC_NHOM = {
    "nhom_1": ["1", "5", "4", "6", "15", "20", "17", "16", "19"],
    "nhom_2": ["9", "10", "11", "12", "3", "8", "14", "2", "7"],
    "nhom_3": ["Q1", "Q2", "Q3", "Q4"],
    "nhom_4": ["21", "22", "23", "24", "W1", "W2", "28", "29", "W7"],
    "nhom_5": ["34", "36", "35", "39", "31", "30", "32", "Q6", "Q7"],
    "nhom_6": ["43", "44", "45", "46", "47"],
    "bang_size": ["bang size", "size", "bảng size", "bảng số đo", "bang so do", "form size"]
}

# Tạo bảng tra cứu ngược từ mã -> ảnh tương đối
ANH_THEO_MA = {}
for ten_nhom, danh_sach_ma in DANH_MUC_NHOM.items():
    duong_dan = f"/static/products/{ten_nhom}.jpg"
    for ma in danh_sach_ma:
        ANH_THEO_MA[ma.upper()] = duong_dan
        ANH_THEO_MA[ma.lower()] = duong_dan

ALL_ANH_QUAN = ["/static/products/nhom_3.jpg", "/static/products/nhom_5.jpg"]
ALL_ANH_AO = [
    "/static/products/nhom_1.jpg",
    "/static/products/nhom_2.jpg",
    "/static/products/nhom_4.jpg",
    "/static/products/nhom_5.jpg",
    "/static/products/nhom_6.jpg"
]
ANH_BANG_SIZE = ["/static/products/bang_size.jpg"]


def chuan_hoa_ma_quan(text: str) -> str:
    """
    Chuẩn hóa các mã quần dính liền (như 'quần 124', 'q124', 'quan 12', 'quần 134', 'quần 24', 'quần 1234')
    thành dạng danh sách mã riêng biệt (như 'quần 1, 2, 4').
    Quần short của Fitman chỉ có các mã đơn lẻ: 1, 2, 3, 4, 6, 7.
    """
    if not text:
        return text

    pattern = re.compile(
        r'(?i)\b(quần|quan|q|short|đùi)\s*([123467]{2,4})\b'
    )

    def replace_match(m):
        prefix = m.group(1)
        digits = m.group(2)
        clean_prefix = "quần" if prefix.lower() in ("q", "quần", "quan") else prefix
        formatted_numbers = ", ".join(digits)
        return f"{clean_prefix} {formatted_numbers}"

    return pattern.sub(replace_match, text)


def tim_anh_san_pham(ma_san_pham_hoac_tu_khoa: str) -> Dict[str, Any]:
    """
    Tìm danh sách ảnh sản phẩm hoặc bảng size dựa trên mã sản phẩm hoặc từ khóa tìm kiếm.
    Hỗ trợ gửi tất cả ảnh cho nhóm quần hoặc nhóm áo khi khách hỏi chung.
    """
    if not ma_san_pham_hoac_tu_khoa:
        return {"ma": "", "image_url": "", "image_urls": [], "found": False}

    # Tiền xử lý chuẩn hóa mã quần dính liền (ví dụ: 'quần 124' -> 'quần 1, 2, 4')
    ma_san_pham_hoac_tu_khoa = chuan_hoa_ma_quan(str(ma_san_pham_hoac_tu_khoa))

    tu_khoa = ma_san_pham_hoac_tu_khoa.strip()
    tu_khoa_lower = tu_khoa.lower()
    tu_khoa_upper = tu_khoa.upper()

    # Chuẩn hóa "quần mẫu N" hoặc "quần 123" -> "Q{N}" trước khi xử lý
    _quan_mau_map = {
        "quần mẫu 1": "Q1", "quan mau 1": "Q1", "mau quan 1": "Q1",
        "quần mẫu 2": "Q2", "quan mau 2": "Q2", "mau quan 2": "Q2",
        "quần mẫu 3": "Q3", "quan mau 3": "Q3", "mau quan 3": "Q3",
        "quần mẫu 4": "Q4", "quan mau 4": "Q4", "mau quan 4": "Q4",
        "quần mẫu 6": "Q6", "quan mau 6": "Q6", "mau quan 6": "Q6",
        "quần mẫu 7": "Q7", "quan mau 7": "Q7", "mau quan 7": "Q7",
    }
    for _phrase, _code in _quan_mau_map.items():
        if _phrase in tu_khoa_lower:
            tu_khoa = _code
            tu_khoa_lower = _code.lower()
            tu_khoa_upper = _code.upper()
            break

    image_urls: List[str] = []

    # 0. Khách hỏi xem mẫu chung chung ("cho xem mẫu", "xem mẫu", "mẫu đâu", "mẫu", "mau", "xem mau", "mẫu mới")
    if any(k in tu_khoa_lower for k in ["cho xem mẫu", "xem mẫu", "mẫu đâu", "cho xem mau", "xem mau", "mẫu mới", "mau moi", "sản phẩm", "san pham"]) or tu_khoa_lower in ("mẫu", "mau"):
        image_urls = ALL_ANH_AO + ALL_ANH_QUAN

    # 1. Khách hỏi xem toàn bộ ảnh Quần
    elif any(k in tu_khoa_lower for k in ["quần", "quan", "short", "đùi"]):
        # Nếu hỏi cụ thể mã quần (Q1, Q2, Q3, Q4, Q6, Q7)
        matched_specific = False
        for q_code in ["Q1", "Q2", "Q3", "Q4", "Q6", "Q7"]:
            if q_code.lower() in tu_khoa_lower.split() or q_code in tu_khoa_upper.split() or q_code.lower() in tu_khoa_lower:
                if ANH_THEO_MA.get(q_code) and ANH_THEO_MA[q_code] not in image_urls:
                    image_urls.append(ANH_THEO_MA[q_code])
                matched_specific = True
        if not matched_specific:
            image_urls = ALL_ANH_QUAN

    # 2. Khách hỏi xem toàn bộ ảnh Áo hoặc xem mẫu chung
    elif tu_khoa_lower in ("áo", "ao") or any(k in tu_khoa_lower for k in ["mẫu áo", "ảnh áo", "áo thun", "xem áo", "cac mau ao", "các mẫu áo"]):
        image_urls = ALL_ANH_AO

    # 3. Khách hỏi bảng size
    elif any(k in tu_khoa_lower for k in ["bảng size", "bang size", "bảng số đo", "bang so do", "size chart", "form size"]):
        image_urls = ANH_BANG_SIZE

    # 4. Tra cứu theo mã nhóm cụ thể (nhom_1, nhom_2, ...)
    elif tu_khoa_lower in DANH_MUC_NHOM:
        image_urls = [f"/static/products/{tu_khoa_lower}.jpg"]

    # 5. Tra cứu theo mã sản phẩm cụ thể (1, 5, 21, W1, Q1, 43, ...)
    elif tu_khoa_upper in ANH_THEO_MA:
        image_urls = [ANH_THEO_MA[tu_khoa_upper]]

    # 6. Tìm mã trong từng từ của câu chat
    else:
        for ma, img in ANH_THEO_MA.items():
            if ma.lower() in tu_khoa_lower.split():
                if img not in image_urls:
                    image_urls.append(img)

    # Không thêm fallback "ao" ở đây vì dễ match sai (vd: "bao", "bao nhiêu")

    return {
        "ma": tu_khoa,
        "image_url": image_urls[0] if image_urls else "",
        "image_urls": image_urls,
        "found": bool(image_urls)
    }


def tinh_size(can_nang: float, chieu_cao: float, loai_san_pham: str = "cả hai") -> dict:
    if can_nang <= 0 or chieu_cao <= 0:
        raise ValueError("Cân nặng và chiều cao phải lớn hơn 0")
    
    if chieu_cao > 3:
        chieu_cao = chieu_cao / 100

    # --- Size Áo ---
    if can_nang < 60:
        ao = "S"
    elif can_nang <= 72:
        ao = "M"
    elif can_nang <= 81:
        ao = "L"
    else:
        ao = "XL"

    # Upsize áo nếu chiều cao < 1.65
    ly_do = ""
    if chieu_cao < 1.65:
        upsize_map = {"S": "M", "M": "L", "L": "XL", "XL": "XL"}
        ao = upsize_map[ao]
        ly_do = "Chiều cao dưới 1m65 nên tự động up 1 size áo để mặc thoải mái. "

    # --- Size Quần ---
    # Quần chỉ có M, L, XL chia đều 55-100kg
    if can_nang <= 66:
        quan = "M"
    elif can_nang <= 75:
        quan = "L"
    else:
        quan = "XL"

    # --- Trả kết quả theo loại sản phẩm ---
    if loai_san_pham == "áo":
        final_size = f"Áo {ao}"
    elif loai_san_pham == "quần":
        final_size = f"Quần {quan}"
    else:
        final_size = f"Áo {ao}, Quần {quan}"

    return {
        "size": final_size,
        "can_nang": can_nang,
        "chieu_cao": chieu_cao,
        "ly_do": ly_do + f"Form chuẩn theo {can_nang}kg."
    }


def tinh_gia(so_luong: int) -> dict:
    if so_luong <= 0:
        raise ValueError("Số lượng phải lớn hơn 0")

    don_gia_co_ban = 150000

    upsell_hint = ""
    if so_luong == 1:
        phi_ship = 30000
        freeship = False
        tong_tien = 180000
        chi_tiet = "1 món: 150.000đ + 30.000đ phí ship = 180.000đ"
        upsell_hint = "Khách chọn 1 món (180k gồm 30k ship). BẮT BUỘC BẠN PHẢI GỢI Ý (UPSELL): Anh lấy thêm 1 món nữa (nếu chọn áo thì gợi ý quần đùi gym) thành combo 2 món chỉ 300k được FREESHIP luôn ạ, bù thêm có 120k là có thêm 1 món mà không tốn 30k tiền ship!"
    elif so_luong == 2:
        phi_ship = 0
        freeship = True
        tong_tien = 300000
        chi_tiet = "2 món: 300.000đ (Freeship)"
        upsell_hint = "Khách chọn 2 món (300k freeship). BẮT BUỘC BẠN PHẢI GỢI Ý (UPSELL CỰC HỜI): Combo 3 món của shop là 400k freeship, nghĩa là CHỈ CẦN THÊM ĐÚNG 100K là có thêm món thứ 3 (nếu khách mua 2 quần thì offer thêm 1 áo chỉ thêm 100k, nếu mua 2 áo thì offer thêm 1 quần chỉ thêm 100k) cực kỳ hời!"
    elif so_luong == 3:
        phi_ship = 0
        freeship = True
        tong_tien = 400000
        chi_tiet = "3 món: 400.000đ combo ưu đãi (Freeship)"
    else:
        phi_ship = 0
        freeship = True
        tong_tien = 400000 + (so_luong - 3) * 130000
        chi_tiet = f"{so_luong} món: 400.000đ combo 3 món + {(so_luong - 3) * 130000:,}đ ({so_luong - 3} món thêm x 130k) = {tong_tien:,}đ (Freeship)"

    tong_tien_format = f"{tong_tien:,}".replace(",", ".") + "đ"

    res = {
        "so_luong": so_luong,
        "don_gia_co_ban": don_gia_co_ban,
        "phi_ship": phi_ship,
        "freeship": freeship,
        "tong_tien": tong_tien,
        "tong_tien_format": tong_tien_format,
        "chi_tiet": chi_tiet
    }
    if upsell_hint:
        res["upsell_hint"] = upsell_hint
    return res


def goi_y_upsell(so_luong: int, danh_sach_mon: Optional[Union[List[str], str]] = None) -> dict:
    """
    Gợi ý kịch bản upsell thông minh theo hành vi chọn đồ của khách:
    1. Khách mua 1 món (180k gồm 30k ship):
       - Gợi ý thêm 1 món chéo (mua áo -> gợi ý quần đùi; mua quần -> gợi ý áo thun gym).
       - Trở thành combo 2 món 300k FREESHIP (bù thêm 120k).
    2. Khách mua 2 món (300k freeship):
       - Gợi ý thêm 1 món chéo (mua 2 quần -> offer thêm 1 áo; mua 2 áo -> offer thêm 1 quần).
       - CHỈ CẦN THÊM ĐÚNG 100K là được combo 3 món 400k cực hời (thay vì giá lẻ 150k)!
    """
    if isinstance(danh_sach_mon, str):
        danh_sach_mon = [danh_sach_mon]
    danh_sach_mon = danh_sach_mon or []
    text_mon = " ".join(danh_sach_mon).lower()

    co_ao = any(k in text_mon for k in ["áo", "ao", "thun", "oversize", "cbum", "wolves"])
    co_quan = any(k in text_mon for k in ["quần", "quan", "short", "đùi", "dui", "q1", "q2", "q3", "q4", "q6", "q7"])

    if co_ao and not co_quan:
        loai_hien_tai = "áo"
        loai_goi_y = "quần đùi tập gym"
    elif co_quan and not co_ao:
        loai_hien_tai = "quần"
        loai_goi_y = "áo thun oversize tập gym"
    else:
        loai_hien_tai = "sản phẩm"
        loai_goi_y = "áo hoặc quần đùi tập gym"

    if so_luong == 1:
        loi_khuyen = (
            f"Dạ {loai_hien_tai} của anh là 180k (đã gồm 30k ship) ạ. "
            f"Shop em đang có ưu đãi combo 2 món chỉ 300k là được FREESHIP luôn ạ, tính ra bù thêm có 120k là anh có thêm 1 {loai_goi_y} "
            f"mặc phối trọn bộ tập cực đẹp mà lại không tốn 30k tiền ship! Anh có muốn chọn thêm 1 mẫu nữa để được freeship không em gửi ảnh anh xem nha? 🔥"
        )
        return {
            "so_luong_hien_tai": 1,
            "gia_hien_tai": "180.000đ (gồm 30k ship)",
            "loi_khuyen_upsell": loi_khuyen,
            "combo_muc_tieu": "2 món 300.000đ (Freeship)",
            "so_tien_bu_them": "120.000đ",
            "mon_goi_y": loai_goi_y
        }
    elif so_luong == 2:
        loi_khuyen = (
            f"Dạ 2 {loai_hien_tai} của anh là 300k và đã được FREESHIP rồi ạ! "
            f"Nhưng Fitman đang có combo 3 món chỉ 400k, tính ra anh lấy thêm 1 {loai_goi_y} nữa CHỈ THÊM CÓ ĐÚNG 100K thôi cực kỳ hời luôn ạ (giá gốc 150k)! "
            f"Anh có muốn chọn thêm 1 {loai_goi_y} cho đủ bộ mặc tập cả tuần không em gửi mẫu anh xem nha? 🔥"
        )
        return {
            "so_luong_hien_tai": 2,
            "gia_hien_tai": "300.000đ (Freeship)",
            "loi_khuyen_upsell": loi_khuyen,
            "combo_muc_tieu": "Combo 3 món 400.000đ (Freeship)",
            "so_tien_bu_them": "100.000đ",
            "mon_goi_y": loai_goi_y
        }
    else:
        return {
            "so_luong_hien_tai": so_luong,
            "loi_khuyen_upsell": "Đơn hàng đã đạt combo ưu đãi tốt nhất của shop rồi ạ! 💪"
        }


async def tao_don_hang(
    danh_sach_mon: Union[List[str], str],
    so_luong: int,
    tong_tien: int,
    so_dien_thoai: str,
    dia_chi: str,
    ten_khach_hang: str = "Khách hàng",
    sender_id: str = ""
) -> dict:
    """
    Tạo đơn hàng chính thức, lưu vào hệ thống và gửi thông báo đơn mới tới shop owner qua Telegram.
    Kiểm tra nghiêm ngặt: SĐT, Địa chỉ, Tổng tiền hợp lệ mới cho phép tạo đơn!
    """
    # 1. Kiểm tra SĐT
    digits_phone = re.sub(r'\D', '', str(so_dien_thoai or ''))
    if len(digits_phone) < 10:
        return {
            "success": False,
            "error": "Chưa có Số Điện Thoại hợp lệ (tối thiểu 10 chữ số). Tuyệt đối CẤM tạo đơn khi chưa có SĐT thật!"
        }

    # 2. Kiểm tra Địa chỉ
    clean_addr = str(dia_chi or "").strip()
    hallucinated_addrs = [
        "chưa có địa chỉ cụ thể", "chưa có địa chỉ", "123 lê lợi", "123 đường lê lợi",
        "địa chỉ bạn đã cung cấp", "địa chỉ khách cung cấp", "địa chỉ của anh", ""
    ]
    if len(clean_addr) < 6 or clean_addr.lower() in hallucinated_addrs:
        return {
            "success": False,
            "error": "Chưa có Địa Chỉ giao hàng cụ thể của khách. Hãy hỏi xin địa chỉ (số nhà, đường, phường...) trước khi tạo đơn!"
        }

    # 3. Kiểm tra Tổng tiền
    try:
        val_tien = int(tong_tien)
    except Exception:
        val_tien = 0
    if val_tien < 100000:
        return {
            "success": False,
            "error": f"Tổng tiền đơn hàng không hợp lệ ({val_tien}đ). Đơn hàng tối thiểu phải từ 150.000đ trở lên. Chưa thể tạo đơn!"
        }

    from app.services.order_service import save_order
    from app.services.telegram_service import send_new_order_notification

    if isinstance(danh_sach_mon, str):
        danh_sach_mon = [danh_sach_mon]

    order_data = {
        "ten_khach_hang": str(ten_khach_hang or "Khách hàng"),
        "danh_sach_mon": danh_sach_mon,
        "so_luong": int(so_luong),
        "tong_tien": val_tien,
        "so_dien_thoai": str(so_dien_thoai),
        "dia_chi": clean_addr,
        "sender_id": str(sender_id)
    }

    saved = save_order(order_data)
    if not saved:
        return {
            "success": False,
            "error": "Lỗi lưu đơn hàng vào hệ thống!"
        }

    telegram_ok = await send_new_order_notification(saved)

    return {
        "success": True,
        "order_id": saved["id"],
        "order_number_today": saved.get("order_number_today", 1),
        "message": f"Đơn hàng {saved['id']} (Đơn #{saved.get('order_number_today', 1)} hôm nay) đã được ghi nhận và gửi thông báo thành công!",
        "telegram_notified": telegram_ok
    }
