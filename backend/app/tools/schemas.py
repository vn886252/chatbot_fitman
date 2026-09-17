from app.tools.business_rules import tinh_size, tinh_gia, tim_anh_san_pham, tao_don_hang

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
    },
    {
        "type": "function",
        "function": {
            "name": "tao_don_hang",
            "description": "Tạo đơn hàng chính thức và gửi thông báo đơn mới đến shop owner qua Telegram. BẮT BUỘC GỌI TOOL NÀY KHI ĐƠN ĐÃ ĐỦ 4 YẾU TỐ: (1) Mã sản phẩm cụ thể (áo 30, quần 1...), (2) Size chữ (S, M, L, XL), (3) SĐT thật 10 số, (4) Địa chỉ giao hàng cụ thể. CẤM gọi tool này nếu thiếu bất kỳ yếu tố nào!",
            "parameters": {
                "type": "object",
                "properties": {
                    "ten_khach_hang": {
                        "type": "string",
                        "description": "Tên khách hàng (nếu biết, mặc định 'Khách hàng')"
                    },
                    "danh_sach_mon": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Danh sách các món cụ thể kèm size (ví dụ: ['1 áo mẫu 30 (size M)', '1 áo mẫu 31 (size M)', '1 quần mẫu 1 (size L)']"
                    },
                    "so_luong": {
                        "type": "integer",
                        "description": "Tổng số lượng món hàng (ví dụ: 3, 5)"
                    },
                    "tong_tien": {
                        "type": "integer",
                        "description": "Tổng số tiền của đơn hàng (ví dụ: 300000, 400000, 660000)"
                    },
                    "so_dien_thoai": {
                        "type": "string",
                        "description": "Số điện thoại nhận hàng của khách (ví dụ: '0794763225')"
                    },
                    "dia_chi": {
                        "type": "string",
                        "description": "Địa chỉ nhận hàng cụ thể của khách"
                    }
                },
                "required": ["danh_sach_mon", "so_luong", "tong_tien", "so_dien_thoai", "dia_chi"]
            }
        }
    }
]

AVAILABLE_FUNCTIONS = {
    "tinh_size": tinh_size,
    "tinh_gia": tinh_gia,
    "tim_anh_san_pham": tim_anh_san_pham,
    "tao_don_hang": tao_don_hang
}
