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


def tim_anh_san_pham(ma_san_pham_hoac_tu_khoa: str) -> Dict[str, Any]:
    """
    Tìm danh sách ảnh sản phẩm hoặc bảng size dựa trên mã sản phẩm hoặc từ khóa tìm kiếm.
    Hỗ trợ gửi tất cả ảnh cho nhóm quần hoặc nhóm áo khi khách hỏi chung.
    """
    if not ma_san_pham_hoac_tu_khoa:
        return {"ma": "", "image_url": "", "image_urls": [], "found": False}

    tu_khoa = str(ma_san_pham_hoac_tu_khoa).strip()
    tu_khoa_lower = tu_khoa.lower()
    tu_khoa_upper = tu_khoa.upper()

    image_urls: List[str] = []

    # 1. Khách hỏi xem toàn bộ ảnh Quần
    if any(k in tu_khoa_lower for k in ["quần", "quan", "short", "đùi"]):
        # Nếu hỏi cụ thể mã quần (Q1, Q2, Q3, Q4, Q6, Q7)
        matched_specific = False
        for q_code in ["Q1", "Q2", "Q3", "Q4", "Q6", "Q7"]:
            if q_code.lower() in tu_khoa_lower.split() or q_code in tu_khoa_upper.split():
                image_urls = [ANH_THEO_MA[q_code]]
                matched_specific = True
                break
        if not matched_specific:
            image_urls = ALL_ANH_QUAN

    # 2. Khách hỏi xem toàn bộ ảnh Áo hoặc xem mẫu chung
    elif any(k in tu_khoa_lower for k in ["mẫu áo", "ảnh áo", "áo thun", "xem áo", "cac mau ao", "các mẫu áo"]):
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

    # Nếu vẫn chưa có và hỏi chung về áo/cbum/mẫu
    if not image_urls and any(k in tu_khoa_lower for k in ["áo", "ao", "cbum", "mẫu", "mau", "xem ảnh"]):
        image_urls = ALL_ANH_AO

    return {
        "ma": tu_khoa,
        "image_url": image_urls[0] if image_urls else "",
        "image_urls": image_urls,
        "found": bool(image_urls)
    }


def tinh_size(can_nang: float, chieu_cao: float) -> dict:
    if can_nang <= 0 or chieu_cao <= 0:
        raise ValueError("Cân nặng và chiều cao phải lớn hơn 0")
    
    if chieu_cao > 3:
        chieu_cao = chieu_cao / 100

    if can_nang < 62.0:
        size_goc = "S"
    elif 62.0 <= can_nang <= 75.0:
        size_goc = "M"
    elif 75.0 < can_nang <= 84.0:
        size_goc = "L"
    else:
        size_goc = "XL"

    if chieu_cao < 1.65:
        co_upsize = True
        if size_goc == "S":
            size = "M"
        elif size_goc == "M":
            size = "L"
        elif size_goc == "L":
            size = "XL"
        else:
            size = "XL"
        ly_do = f"Chiều cao {chieu_cao:.2f}m thấp hơn 1.65m nên tăng 1 size từ {size_goc} lên {size} để mặc thoải mái"
    else:
        co_upsize = False
        size = size_goc
        ly_do = f"Chiều cao {chieu_cao:.2f}m chuẩn form size {size}"

    return {
        "size": size,
        "size_goc": size_goc,
        "can_nang": can_nang,
        "chieu_cao": chieu_cao,
        "co_upsize": co_upsize,
        "ly_do": ly_do
    }


def tinh_gia(so_luong: int) -> dict:
    if so_luong <= 0:
        raise ValueError("Số lượng phải lớn hơn 0")

    don_gia_co_ban = 150000

    if so_luong == 1:
        phi_ship = 30000
        freeship = False
        tong_tien = 180000
        chi_tiet = "1 món: 150.000đ + 30.000đ phí ship = 180.000đ"
    elif so_luong == 2:
        phi_ship = 0
        freeship = True
        tong_tien = 300000
        chi_tiet = "2 món: 300.000đ (Freeship)"
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

    return {
        "so_luong": so_luong,
        "don_gia_co_ban": don_gia_co_ban,
        "phi_ship": phi_ship,
        "freeship": freeship,
        "tong_tien": tong_tien,
        "tong_tien_format": tong_tien_format,
        "chi_tiet": chi_tiet
    }
