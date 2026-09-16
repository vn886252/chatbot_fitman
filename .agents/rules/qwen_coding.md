# Rule: Luôn gọi Qwen local để viết code

## Ràng buộc BẮT BUỘC
Khi làm việc trong workspace này (FITMAN project), **TUYỆT ĐỐI KHÔNG tự viết code**.
Mọi thay đổi code phải được viết bởi **Qwen local tại `http://localhost:5001`**.

## Quy trình bắt buộc khi cần viết/sửa code

1. **Phân tích**: Đọc file liên quan, hiểu rõ vấn đề/yêu cầu.
2. **Soạn prompt**: Viết prompt rõ ràng cho Qwen (mô tả bug/yêu cầu, file cần sửa, đoạn code cần thay).
3. **Gọi Qwen**: Gửi request tới `http://localhost:5001/v1/chat/completions` (lưu output ra file `.txt` để tránh encoding lỗi).
4. **Review**: Đọc output của Qwen, đánh giá logic có đúng không.
5. **Apply**: Áp dụng code Qwen viết vào file (dùng replace/multi_replace tool).
6. **Verify**: Chạy syntax check (`ast.parse`) và test logic nếu cần.
7. **Push**: Commit và push lên GitHub.

## Ngoại lệ (KHÔNG cần gọi Qwen)
- Sửa **text thuần túy** (system prompt, comments, git message)
- Sửa lỗi cực nhỏ 1 ký tự (typo, missing quote)
- Qwen local **không chạy** (đã thử connect thất bại) → báo user biết trước khi tự viết

## Cách gọi Qwen (template script)
```python
import urllib.request, json

PROMPT = "..."  # mô tả yêu cầu rõ ràng

data = json.dumps({
    "model": "koboldcpp/Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
    "messages": [{"role": "user", "content": PROMPT}],
    "max_tokens": 1000,
    "temperature": 0.1
}).encode()

req = urllib.request.Request(
    "http://localhost:5001/v1/chat/completions",
    data=data, headers={"Content-Type": "application/json"}, method="POST"
)
resp = urllib.request.urlopen(req, timeout=90)
result = json.loads(resp.read().decode())
with open("qwen_output.txt", "w", encoding="utf-8") as f:
    f.write(result["choices"][0]["message"]["content"])
print("Done. Check qwen_output.txt")
```
