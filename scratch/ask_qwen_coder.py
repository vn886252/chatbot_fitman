import urllib.request
import json

PROMPT = """Bạn là trợ lý AI. Hãy sửa code Python trong 2 file của dự án Fitman:

FILE 1: backend/app/tools/business_rules.py
Hàm `tim_anh_san_pham(ma_san_pham_hoac_tu_khoa: str)`:
Hiện tại khi khách hỏi xem mẫu chung chung như:
- "cho xem mẫu", "xem mẫu", "mẫu đâu", "xem mau", "mau", "cho xem mau", "xem sản phẩm"
Thì hàm không match nhánh nào và trả về image_urls rỗng, khiến bot nói gửi mẫu nhưng không có ảnh nào được gửi!
Ngoài ra:
- Khách nói "quần 123" hoặc "quần 1 2 3" hoặc "1 2 3": cần nhận diện được đó là các mã quần Q1, Q2, Q3.

FILE 2: backend/app/services/llm_service.py
Dòng 183-186:
    # Nếu LLM gọi tinh_size mà chưa có ảnh → gửi bảng size
    if not suggested_images and "tinh_size" in tool_calls_made:
        suggested_images = ["/static/products/bang_size.jpg"]
Vấn đề: Cứ mỗi lần gọi tinh_size là lại gửi đính kèm bang_size.jpg, khiến khách bị SPAM ảnh bảng size liên tục mỗi lượt chat rất khó chịu!
Khách chỉ muốn xem bảng size khi họ HỎI xem bảng size ("bảng size", "bang size", "size chart").
Hãy BỎ đoạn tự động gửi bang_size.jpg khi gọi tinh_size này đi.
Đồng thời ở phần keyword matching (dòng 165-182):
Nếu user nói xem mẫu chung chung ("xem mẫu", "cho xem mẫu", "mẫu", "mau", "xem mau"):
Gửi ảnh mẫu áo + quần (hoặc ảnh mẫu áo).

Hãy viết code chỉnh sửa chuẩn xác cho 2 file trên. Trả về dưới dạng code python rõ ràng.
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
    with open("scratch/qwen_code_fix.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Done! Length:", len(content))
except Exception as e:
    print("Error:", e)
