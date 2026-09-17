import json
import urllib.request

PROMPT = """
Viết một hàm Python `chuan_hoa_ma_quan(text: str) -> str`.

[MỤC ĐÍCH]:
Shop thời trang FITMAN có sản phẩm quần short CHỈ CÓ các mã số hợp lệ là: 1, 2, 3, 4, 6, 7 (tương ứng Q1, Q2, Q3, Q4, Q6, Q7).
Shop KHÔNG CÓ mã quần nào gồm 2 chữ số hay 3 chữ số (không có quần 12, 14, 24, 124, 134, 1234...).
Khi khách nhắn tin đặt hàng hoặc hỏi mẫu, họ thường gõ liền chuỗi số cho quần, ví dụ:
- "lấy tôi áo 30 31 quần 124 đi shop" -> tách thành "lấy tôi áo 30 31 quần 1, 2, 4 đi shop"
- "quần 12" -> "quần 1, 2"
- "quần 134" -> "quần 1, 3, 4"
- "quần 24" -> "quần 2, 4"
- "quần 1234" -> "quần 1, 2, 3, 4"
- "q124" hoặc "Q124" -> "quần 1, 2, 4"
- "quan 12" -> "quan 1, 2"

[RÀNG BUỘC QUAN TRỌNG]:
1. Chỉ tách chuỗi số khi đi liền sau các từ chỉ quần: "quần", "quan", "q", "short", "đùi" (không phân biệt hoa thường).
2. Chuỗi số phải gồm từ 2 chữ số trở lên và MỌI chữ số trong chuỗi đó phải thuộc tập {1, 2, 3, 4, 6, 7}.
3. TUYỆT ĐỐI KHÔNG chạm vào số điện thoại (ví dụ "0794763225" hoặc các dãy 10-11 số).
4. TUYỆT ĐỐI KHÔNG chạm vào mã áo (ví dụ "áo 30 31", "áo 46 47", "áo 12").
5. TUYỆT ĐỐI KHÔNG chạm vào số đo chiều cao cân nặng (ví dụ "1m70", "70kg", "170cm").
6. Nếu chuỗi đã cách nhau bằng dấu cách hoặc phẩy (ví dụ "quần 1 2 4", "quần 1, 2, 4") hoặc là mã đơn ("quần 1", "quần 4", "Q1") thì xử lý hợp lý, không làm hỏng.

CHỈ TRẢ VỀ CODE PYTHON ĐẦY ĐỦ CỦA HÀM `chuan_hoa_ma_quan(text: str) -> str` VÀ CÁC TEST CASES ĐI KÈM. KHÔNG GIẢI THÍCH DÀI DÒNG.
"""

data = json.dumps({
    "model": "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "messages": [{"role": "user", "content": PROMPT}],
    "max_tokens": 1500,
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
    print("Calling Unsloth (port 8888)...")
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read().decode("utf-8"))
    content = result["choices"][0]["message"]["content"]
    with open("scratch/unsloth_quan_output.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Success! Output saved to scratch/unsloth_quan_output.txt")
except Exception as e:
    print(f"Error calling Unsloth: {e}")
