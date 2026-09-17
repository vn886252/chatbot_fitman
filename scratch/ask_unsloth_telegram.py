import json
import urllib.request

PROMPT = """
Viết 2 module Python cho hệ thống shop thời trang FITMAN:

Module 1: `order_service.py`
Mục đích: Quản lý lưu trữ đơn hàng và tính toán doanh thu ngày.
Yêu cầu:
1. Lưu đơn vào file JSON tại `app/data/orders.json` (đường dẫn tuyệt đối hoặc tương đối an toàn so với file). Tự tạo file nếu chưa tồn tại.
2. Hàm `save_order(order_data: dict) -> dict`:
   - Input: dict chứa:
     `ten_khach_hang` (str)
     `danh_sach_mon` (list[str])
     `so_luong` (int)
     `tong_tien` (int)
     `so_dien_thoai` (str)
     `dia_chi` (str)
     `sender_id` (optional str)
   - Tự động sinh `id` (ví dụ `ORD-YYYYMMDD-XXXX`), `created_at` (giờ VN UTC+7 YYYY-MM-DD HH:MM:SS), `date` (YYYY-MM-DD).
   - Lưu vào file `orders.json` và trả về dict đơn hàng đã lưu.
3. Hàm `get_daily_summary(target_date: str = None) -> dict`:
   - Nếu `target_date` None, lấy ngày hôm nay theo giờ VN UTC+7.
   - Lọc tất cả đơn hàng có `date == target_date`.
   - Trả về dict:
     `date`: str
     `total_orders`: int
     `total_items`: int (tổng số lượng sản phẩm)
     `total_revenue`: int (tổng tiền)
     `orders`: list các đơn hàng trong ngày

Module 2: `telegram_service.py`
Mục đích: Gửi thông báo đơn hàng mới và báo cáo doanh thu ngày qua Telegram Bot API.
Yêu cầu:
1. Đọc `settings.TELEGRAM_BOT_TOKEN` và `settings.TELEGRAM_CHAT_ID` từ `app.config import settings`.
2. Hàm async `send_telegram_message(text: str, parse_mode: str = "HTML") -> bool`:
   Dùng `httpx.AsyncClient` gọi `https://api.telegram.org/bot{token}/sendMessage`.
3. Hàm async `send_new_order_notification(order: dict) -> bool`:
   - Format tin nhắn HTML đẹp, có emoji:
     🔔 ĐƠN HÀNG MỚI TỪ FITMAN CHATBOT!
     👤 Khách hàng: ...
     📞 SĐT: ...
     📍 Địa chỉ: ...
     📦 Số lượng: ... món
     📋 Chi tiết:
     (liệt kê từng món)
     💰 Tổng tiền: ... (format số có dấu chấm/phẩy)
     ⏰ Thời gian: ...
   - Gửi qua Telegram và trả về True/False.
4. Hàm async `send_daily_revenue_report(target_date: str = None) -> bool`:
   - Gọi `get_daily_summary(target_date)`.
   - Format tin nhắn HTML báo cáo tổng kết ngày:
     📊 BÁO CÁO DOANH THU NGÀY ...
     🛒 Tổng số đơn: ...
     👕 Tổng sản phẩm: ...
     💰 Tổng doanh thu: ...
     (Chi tiết tóm tắt từng đơn nếu có)
   - Gửi qua Telegram và trả về True/False.

CHỈ TRẢ VỀ CODE PYTHON CỦA CẢ 2 MODULE (phân tách rõ ràng bằng comment hoặc markdown block). KHÔNG GIẢI THÍCH DÀI DÒNG.
"""

data = json.dumps({
    "model": "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "messages": [{"role": "user", "content": PROMPT}],
    "max_tokens": 2500,
    "temperature": 0.1
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:8888/v1/chat/completions",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-unsloth-f9c9f456bca0cf8793c9dfcee857115d"
    },
    method="POST"
)

try:
    print("Calling Unsloth (port 8888) for Telegram & Order services...")
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read().decode("utf-8"))
    content = result["choices"][0]["message"]["content"]
    with open("scratch/unsloth_telegram_output.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Success! Output saved to scratch/unsloth_telegram_output.txt")
except Exception as e:
    print(f"Error calling Unsloth: {e}")
