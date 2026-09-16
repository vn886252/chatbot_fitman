from app.tools.business_rules import tinh_size, tinh_gia, tim_anh_san_pham

FITMAN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tinh_size",
            "description": "Tính size quần áo chuẩn xác cho khách hàng dựa trên cân nặng (kg) và chiều cao (mét hoặc cm). Bắt buộc gọi hàm này khi khách hỏi tư vấn size hoặc cung cấp chiều cao cân nặng.",
            "parameters": {
                "type": "object",
                "properties": {
                    "can_nang": {
                        "type": "number",
                        "description": "Cân nặng tính bằng kg (ví dụ: 68, 75)"
                    },
                    "chieu_cao": {
                        "type": "number",
                        "description": "Chiều cao tính bằng mét (ví dụ: 1.65, 1.7) hoặc cm (165, 170)"
                    },
                    "loai_san_pham": {
                        "type": "string",
                        "enum": ["áo", "quần", "cả hai"],
                        "description": "Loại sản phẩm khách muốn tư vấn size (áo, quần, hoặc cả hai nếu mua nguyên bộ)."
                    }
                },
                "required": ["can_nang", "chieu_cao", "loai_san_pham"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tinh_gia",
            "description": "Tính tổng tiền và phí ship theo chính sách số lượng sản phẩm (áo và quần đồng giá 150k, freeship từ 2 món, combo từ 3 món). Bắt buộc gọi hàm này khi khách hỏi giá theo số lượng hoặc chốt đơn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "so_luong": {
                        "type": "integer",
                        "description": "Tổng số lượng sản phẩm áo + quần cộng lại (ví dụ: mua 2 áo 1 quần thì so_luong là 3)"
                    }
                },
                "required": ["so_luong"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tim_anh_san_pham",
            "description": "Tìm kiếm đường dẫn ảnh sản phẩm tương ứng với mã áo/quần hoặc bảng size (ví dụ: mã '1', 'W1', 'Q1', 'Q6', 'nhom_1', 'bảng size').",
            "parameters": {
                "type": "object",
                "properties": {
                    "ma_san_pham_hoac_tu_khoa": {
                        "type": "string",
                        "description": "Mã sản phẩm (1, 5, W1, Q1, Q6, 43, nhom_1...) hoặc từ khóa (bảng size, áo, quần...)"
                    }
                },
                "required": ["ma_san_pham_hoac_tu_khoa"]
            }
        }
    }
]

AVAILABLE_FUNCTIONS = {
    "tinh_size": tinh_size,
    "tinh_gia": tinh_gia,
    "tim_anh_san_pham": tim_anh_san_pham
}
