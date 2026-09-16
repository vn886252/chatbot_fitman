import urllib.request
import json

PROMPT = """Bạn là trợ lý AI chuyên tối ưu prompt cho chatbot bán hàng (bằng tiếng Việt).
Tôi cần bạn viết các quy tắc (rules) ngắn gọn, sắc bén, dứt khoát bằng tiếng Việt để thêm vào System Prompt của chatbot bán hàng Fitman.

BỐI CẢNH & 2 BUG CẦN NGĂN CHẶN TRIỆT ĐỂ:

1. BUG 1 (Ảnh 1): Khách nhắn "lấy a áo 1 3 4 quần 123" (tức là chọn mẫu áo 1, 3, 4 và mẫu quần 1, 2, 3).
Bot lại tự hiểu 1, 3, 4 và Q1, Q2, Q3 là SIZE ("1 áo size 1, 1 áo size 3...").
Và vì tưởng khách đã có size nên bot nhảy thẳng sang chốt đơn, tính tiền và xin SĐT/địa chỉ trong khi khách CHƯA HỀ TƯ VẤN SIZE hay chọn size chuẩn S/M/L/XL!
Thực tế:
- Áo shop chỉ có size: S, M, L, XL
- Quần shop chỉ có size: M, L, XL
- Tuyệt đối không có size số (size 1, 2, 3...) hay size mã (size Q1, Q2...). Các con số/ký hiệu đó là MÃ MẪU SẢN PHẨM.
- Nếu khách mới chỉ chọn mẫu hoặc số lượng mà CHƯA có size chữ S/M/L/XL hợp lệ và CHƯA có số đo -> BẮT BUỘC hỏi chiều cao cân nặng để tư vấn size trước, TUYỆT ĐỐI KHÔNG ĐƯỢC CHỐT ĐƠN!

2. BUG 2 (Ảnh 2): Khách hỏi "mẫu mới giá sao shop".
Bot lại liệt kê:
- 1 món: 180k (30k ship)
- 2 món: 300k (freeship)
- 3 món: 400k (combo, freeship)
- 4+ món: 400k + (n-3)x130k (freeship)
Khách phàn nàn: Bắt khách làm toán, thay vì thế hãy nói tự nhiên "từ món thứ 4 trở đi chỉ 130k/món thôi".

Hãy viết thành các phần rõ ràng để nhúng trực tiếp vào System Prompt:
- Bảng giá & cách tư vấn giá (không công thức toán học)
- Phân biệt mã mẫu và size chữ hợp lệ
- Quy trình tư vấn size trước khi chốt đơn.
Viết súc tích, ngắn gọn, dễ hiểu để LLM tuân thủ 100%.
"""

data = json.dumps({
    "model": "koboldcpp/Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
    "messages": [{"role": "user", "content": PROMPT}],
    "max_tokens": 2048,
    "temperature": 0.2
}).encode()

req = urllib.request.Request(
    "http://localhost:5001/v1/chat/completions",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    resp = urllib.request.urlopen(req, timeout=90)
    result = json.loads(resp.read().decode())
    content = result["choices"][0]["message"]["content"]
    with open("scratch/qwen_rules_out.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Done! Content saved to scratch/qwen_rules_out.txt")
except Exception as e:
    print("Error:", e)
