import pytest
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tools.business_rules import tinh_size, tinh_gia, tim_anh_san_pham

class TestTinhSize:
    """Kiểm thử toàn diện 100% logic tính size quần áo FITMAN"""

    def test_size_s_no_upsize(self):
        result = tinh_size(can_nang=60.0, chieu_cao=1.70)
        assert result["size"] == "S"
        assert result["size_goc"] == "S"
        assert result["co_upsize"] is False

    def test_size_s_with_upsize(self):
        result = tinh_size(can_nang=60.0, chieu_cao=1.60)
        assert result["size"] == "M"
        assert result["size_goc"] == "S"
        assert result["co_upsize"] is True
        assert "tăng 1 size từ S lên M" in result["ly_do"]

    def test_size_m_no_upsize(self):
        result = tinh_size(can_nang=70.0, chieu_cao=1.70)
        assert result["size"] == "M"
        assert result["size_goc"] == "M"
        assert result["co_upsize"] is False

    def test_size_m_with_upsize(self):
        result = tinh_size(can_nang=70.0, chieu_cao=1.60)
        assert result["size"] == "L"
        assert result["size_goc"] == "M"
        assert result["co_upsize"] is True
        assert "tăng 1 size từ M lên L" in result["ly_do"]

    def test_size_l_no_upsize(self):
        result = tinh_size(can_nang=80.0, chieu_cao=1.75)
        assert result["size"] == "L"
        assert result["size_goc"] == "L"
        assert result["co_upsize"] is False

    def test_size_l_with_upsize(self):
        result = tinh_size(can_nang=80.0, chieu_cao=1.60)
        assert result["size"] == "XL"
        assert result["size_goc"] == "L"
        assert result["co_upsize"] is True
        assert "tăng 1 size từ L lên XL" in result["ly_do"]

    def test_size_xl_no_upsize(self):
        result = tinh_size(can_nang=90.0, chieu_cao=1.75)
        assert result["size"] == "XL"
        assert result["size_goc"] == "XL"
        assert result["co_upsize"] is False

    def test_size_xl_with_upsize_max(self):
        result = tinh_size(can_nang=90.0, chieu_cao=1.60)
        assert result["size"] == "XL"
        assert result["size_goc"] == "XL"
        assert result["co_upsize"] is True

    def test_boundary_values(self):
        assert tinh_size(61.9, 1.70)["size"] == "S"
        assert tinh_size(62.0, 1.70)["size"] == "M"
        assert tinh_size(75.0, 1.70)["size"] == "M"
        assert tinh_size(75.1, 1.70)["size"] == "L"
        assert tinh_size(84.0, 1.70)["size"] == "L"
        assert tinh_size(85.0, 1.70)["size"] == "XL"

    def test_height_in_cm(self):
        result = tinh_size(can_nang=70.0, chieu_cao=160.0)
        assert result["chieu_cao"] == 1.60
        assert result["size"] == "L"

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            tinh_size(can_nang=0, chieu_cao=1.70)
        with pytest.raises(ValueError):
            tinh_size(can_nang=70, chieu_cao=-1.70)


class TestTinhGia:
    """Kiểm thử toàn diện 100% logic tính giá & phí vận chuyển FITMAN"""

    def test_so_luong_1(self):
        result = tinh_gia(1)
        assert result["tong_tien"] == 180000
        assert result["phi_ship"] == 30000
        assert result["freeship"] is False
        assert result["tong_tien_format"] == "180.000đ"

    def test_so_luong_2(self):
        result = tinh_gia(2)
        assert result["tong_tien"] == 300000
        assert result["phi_ship"] == 0
        assert result["freeship"] is True
        assert result["tong_tien_format"] == "300.000đ"

    def test_so_luong_3(self):
        result = tinh_gia(3)
        assert result["tong_tien"] == 400000
        assert result["phi_ship"] == 0
        assert result["freeship"] is True
        assert result["tong_tien_format"] == "400.000đ"

    def test_so_luong_4(self):
        result = tinh_gia(4)
        assert result["tong_tien"] == 530000
        assert result["phi_ship"] == 0
        assert result["freeship"] is True
        assert result["tong_tien_format"] == "530.000đ"

    def test_so_luong_5(self):
        result = tinh_gia(5)
        assert result["tong_tien"] == 660000
        assert result["phi_ship"] == 0
        assert result["freeship"] is True
        assert result["tong_tien_format"] == "660.000đ"

    def test_so_luong_7(self):
        result = tinh_gia(7)
        assert result["tong_tien"] == 920000
        assert result["phi_ship"] == 0
        assert result["freeship"] is True
        assert result["tong_tien_format"] == "920.000đ"

    def test_invalid_so_luong(self):
        with pytest.raises(ValueError):
            tinh_gia(0)
        with pytest.raises(ValueError):
            tinh_gia(-5)


class TestTimAnhSanPham:
    """Kiểm thử tra cứu ảnh theo mã sản phẩm và bảng size"""

    def test_tim_nhom_1_ma(self):
        for ma in ["1", "5", "4", "6", "15", "20", "17", "16", "19"]:
            res = tim_anh_san_pham(ma)
            assert res["found"] is True
            assert res["image_url"] == "/static/products/nhom_1.jpg"

    def test_tim_nhom_2_ma(self):
        for ma in ["9", "10", "11", "12", "3", "8", "14", "2", "7"]:
            res = tim_anh_san_pham(ma)
            assert res["found"] is True
            assert res["image_url"] == "/static/products/nhom_2.jpg"

    def test_tim_nhom_3_quan(self):
        for ma in ["Q1", "Q2", "Q3", "Q4", "q1", "q2"]:
            res = tim_anh_san_pham(ma)
            assert res["found"] is True
            assert res["image_url"] == "/static/products/nhom_3.jpg"

    def test_tim_nhom_4_wolves(self):
        for ma in ["21", "22", "23", "24", "W1", "W2", "28", "29", "W7", "w1"]:
            res = tim_anh_san_pham(ma)
            assert res["found"] is True
            assert res["image_url"] == "/static/products/nhom_4.jpg"

    def test_tim_nhom_5_champion_quan(self):
        for ma in ["34", "36", "35", "39", "31", "30", "32", "Q6", "Q7", "q6"]:
            res = tim_anh_san_pham(ma)
            assert res["found"] is True
            assert res["image_url"] == "/static/products/nhom_5.jpg"

    def test_tim_nhom_6_olympia(self):
        for ma in ["43", "44", "45", "46", "47"]:
            res = tim_anh_san_pham(ma)
            assert res["found"] is True
            assert res["image_url"] == "/static/products/nhom_6.jpg"

    def test_tim_bang_size(self):
        for kw in ["bang size", "size", "bảng size", "bảng số đo"]:
            res = tim_anh_san_pham(kw)
            assert res["found"] is True
            assert res["image_url"] == "/static/products/bang_size.jpg"

    def test_tim_all_anh_quan(self):
        for kw in ["xem ảnh quần", "ảnh quần", "mẫu quần", "quan short", "quần đùi"]:
            res = tim_anh_san_pham(kw)
            assert res["found"] is True
            assert "/static/products/nhom_3.jpg" in res["image_urls"]
            assert "/static/products/nhom_5.jpg" in res["image_urls"]
            assert len(res["image_urls"]) == 2

    def test_tim_all_anh_ao(self):
        for kw in ["xem ảnh áo", "ảnh áo", "mẫu áo", "các mẫu áo"]:
            res = tim_anh_san_pham(kw)
            assert res["found"] is True
            assert "/static/products/nhom_1.jpg" in res["image_urls"]
            assert "/static/products/nhom_2.jpg" in res["image_urls"]
            assert "/static/products/nhom_4.jpg" in res["image_urls"]
            assert "/static/products/nhom_5.jpg" in res["image_urls"]
            assert "/static/products/nhom_6.jpg" in res["image_urls"]
            assert len(res["image_urls"]) == 5
