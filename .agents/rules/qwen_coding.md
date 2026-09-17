# Rule: Phân vai Claude (Kỹ sư trưởng) + Unsloth (Code Worker)

## Mục tiêu
Tiết kiệm token của model đắt tiền (Claude Opus/Sonnet, Gemini Flash) bằng cách **delegate viết code** cho Unsloth local. Claude chỉ phân tích, ra lệnh, review — KHÔNG tự viết code.

---

## Phân vai

### 🧠 Claude (Kỹ sư trưởng) — KHÔNG viết code
**Nhiệm vụ:**
- Đọc code, phân tích bug, hiểu kiến trúc
- Lên kế hoạch fix/feature (file nào, sửa gì, logic ra sao)
- **Soạn prompt ngắn gọn** cho Unsloth (mô tả yêu cầu, context tối thiểu)
- Review output của Unsloth (đúng logic? đúng style? có bug?)
- Apply code vào file (dùng replace/multi_replace tool)
- Commit, push, deploy
- Trả lời user, báo cáo

**Token tiết kiệm:**
- KHÔNG generate code dài → giảm completion tokens
- Prompt cho Unsloth ngắn gọn (~200-500 tokens) thay vì tự suy nghĩ + viết (~500-2000 tokens)
- Ước tính tiết kiệm **40-60% completion tokens** mỗi task

### 🔧 Unsloth (Code Worker) — CHỈ viết code
**Endpoint:** `http://127.0.0.1:8888/v1/chat/completions`
**API Key:** `Bearer sk-unsloth-f9c9f456bca0cf8793c9dfcee857115d`
**Model:** `qwen-coder`

**Nhiệm vụ:**
- Nhận prompt từ Claude → viết code Python
- Viết hàm mới, sửa hàm cũ, refactor
- Viết regex, logic xử lý, utility functions
- Viết test scripts

**KHÔNG làm:**
- ❌ Không role-play (chatbot bán hàng, prompt design)
- ❌ Không viết text/copy (system prompt, message templates)
- ❌ Không quyết định kiến trúc
- ❌ Không trực tiếp tương tác với user

---

## Quy trình làm việc

```
User yêu cầu
    ↓
Claude phân tích (đọc code, hiểu bug/yêu cầu)
    ↓
Claude soạn prompt cho Unsloth (ngắn gọn, rõ ràng)
    ↓
Gọi Unsloth viết code ──→ Lưu output ra file .txt
    ↓
Claude review output (đúng? sai? cần sửa?)
    ├── Nếu OK → Apply vào source code
    └── Nếu sai → Soạn prompt sửa, gọi lại Unsloth
    ↓
Claude verify (syntax check, test)
    ↓
Claude commit + push + deploy
```

---

## Ngoại lệ (Claude TỰ LÀM, không gọi Unsloth)

1. **Sửa text thuần túy**: system prompt, comments, git message, README
2. **Sửa config/env**: .env, settings, constants
3. **Fix typo**: 1-2 ký tự sai
4. **Unsloth offline**: đã thử connect thất bại → báo user trước khi tự viết
5. **Quá nhỏ**: thêm/xóa 1-2 dòng code đơn giản (import, print, return)

---

## Cách gọi Unsloth (Template)

### Qua MCP tool (ưu tiên nếu có)
Dùng `ask_qwen` MCP tool nếu KoboldCpp (5001) đang chạy.

### Qua HTTP request (khi dùng Unsloth 8888)
```python
import urllib.request, json

PROMPT = """
[YÊU CẦU]: Mô tả ngắn gọn cần viết gì
[FILE]: path/to/file.py
[HÀM CẦN SỬA]: tên hàm (nếu sửa hàm cũ)
[CODE HIỆN TẠI]:
```python
# paste đoạn code cần sửa (tối thiểu, chỉ phần liên quan)
```
[OUTPUT MONG MUỐN]: Mô tả kết quả
CHỈ TRẢ VỀ CODE, KHÔNG GIẢI THÍCH.
"""

data = json.dumps({
    "model": "qwen-coder",
    "messages": [{"role": "user", "content": PROMPT}],
    "max_tokens": 1500,
    "temperature": 0.1
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:8888/v1/chat/completions",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-unsloth-f9c9f456bca0cf8793c9dfcee857115d"
    },
    method="POST"
)
resp = urllib.request.urlopen(req, timeout=120)
result = json.loads(resp.read().decode())
with open("qwen_output.txt", "w", encoding="utf-8") as f:
    f.write(result["choices"][0]["message"]["content"])
```

---

## Mẹo soạn prompt cho Unsloth (tiết kiệm token Claude)

1. **Chỉ paste code liên quan** — KHÔNG paste cả file, chỉ hàm cần sửa
2. **Mô tả ngắn gọn** — 2-3 câu là đủ, không cần giải thích dài
3. **Yêu cầu "chỉ trả code"** — tránh Unsloth giải thích dài dòng
4. **Max tokens vừa đủ** — 500-1500 tùy độ phức tạp, không set 4000
5. **Temperature 0.1** — deterministic, code ổn định hơn

## Ước tính token tiết kiệm

| Task type | Claude tự viết | Claude + Unsloth | Tiết kiệm |
|---|---|---|---|
| Fix bug nhỏ (1 hàm) | ~800 tokens | ~400 tokens | ~50% |
| Viết hàm mới | ~1,500 tokens | ~600 tokens | ~60% |
| Refactor module | ~3,000 tokens | ~1,200 tokens | ~60% |
| Fix text/prompt | ~300 tokens | N/A (tự làm) | 0% |
