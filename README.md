# Chatbot Fanpage FITMAN (Gym/CBUM Style)

Hệ thống Chatbot AI thông minh cho thương hiệu thời trang thể thao **FITMAN** (quần áo oversize phong cách Gym Bro / Thể hình / CBUM).

---

## 👥 Phân Vai Hệ Thống (AI Role Architecture)

- **Kỹ sư trưởng (Lead Architect & QA)**: **Antigravity**
  - Chịu trách nhiệm lập kế hoạch, phân tích đặc tả kỹ thuật, thiết kế cấu trúc hệ thống.
  - Quản lý điều phối, giao nhiệm vụ sinh mã cho Coder và kiểm thử tự động (Pytest).
  - Không trực tiếp code logic mà ủy quyền cho Coder Qwen.
- **Coder chuyên trách (Dedicated AI Coder)**: **Qwen 3 Coder Local (`http://localhost:5001/v1`)**
  - Viết 100% mã nguồn dự án theo đặc tả từ Kỹ sư trưởng thông qua `bridge/qwen_bridge.py`.
  - Thực hiện review và tối ưu hóa code.
- **Chatbot tư vấn khách hàng (Customer Chat Service)**: **OpenAI GPT-4o-mini**
  - Đóng vai trò chuyên viên tư vấn Fitman Gym Bro / CBUM tone để trả lời tin nhắn của khách trên Facebook Fanpage Webhook và xử lý Function Calling.
3. **Tích hợp Facebook Messenger Fanpage Webhook**:
   - Tự động xác thực Webhook (`hub.verify_token`, `hub.challenge`).
   - Gửi tin nhắn trả lời văn bản & tự động đính kèm ảnh sản phẩm/bảng size trực quan.
4. **Tự động gửi ảnh sản phẩm theo ngữ cảnh**:
   - Tư vấn size -> Đính kèm `/static/products/bang_size.jpg`.
   - Hỏi áo CBUM -> Đính kèm `/static/products/nhom_1.jpg`.
   - Hỏi quần short -> Đính kèm `/static/products/nhom_3.jpg`.

---

## 📁 Cấu Trúc Dự Án

```
f:\project fitman\
├── static/
│   └── products/                  # 7 file ảnh sản phẩm & bảng size
│       ├── bang_size.jpg
│       ├── nhom_1.jpg ... nhom_6.jpg
├── backend/
│   ├── app/
│   │   ├── config.py              # Đọc cấu hình môi trường (.env)
│   │   ├── main.py                # FastAPI Server + Static Files mount
│   │   ├── data/catalog.json      # Danh mục chi tiết các nhóm sản phẩm
│   │   ├── prompts/system_prompt.py # Prompt chuẩn Gym Bro CBUM tone
│   │   ├── routers/webhook.py     # Endpoint Webhook Facebook
│   │   ├── services/
│   │   │   ├── llm_service.py     # Xử lý OpenAI / Qwen local + Tool Loop
│   │   │   └── facebook_service.py# Gửi tin nhắn qua Facebook Graph API
│   │   └── tools/
│   │       ├── business_rules.py  # Logic cốt lõi tính size & tính giá
│   │       └── schemas.py         # OpenAI-compatible Function Schemas
│   └── tests/
│       ├── test_business_rules.py # Test 100% các ca size và giá
│       ├── test_webhook_flow.py   # Test luồng Webhook & Static Server
│       └── test_llm_tool_calling.py # Test gọi Function Calling thực tế
├── bridge/
│   └── qwen_bridge.py             # Script kiểm tra & giao tiếp Qwen 3 Coder
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Local

### 1. Cài đặt thư viện
```powershell
pip install -r requirements.txt
```

### 2. Cấu hình file `.env`
Sao chép `.env.example` thành `.env` và kiểm tra các thông số:
```ini
PORT=8000
HOST=0.0.0.0
USE_LOCAL_LLM=true
QWEN_API_BASE=http://127.0.0.1:5001/v1
```

### 3. Kiểm tra kết nối Qwen 3 Coder Local
Đảm bảo KoboldCpp đang chạy trên port 5001:
```powershell
python bridge/qwen_bridge.py
```

### 4. Chạy Backend Server
```powershell
uvicorn app.main:app --reload --port 8000 --app-dir backend
```
- API Docs: `http://localhost:8000/docs`
- Test ảnh bảng size: `http://localhost:8000/static/products/bang_size.jpg`
- Test ảnh mẫu áo CBUM: `http://localhost:8000/static/products/nhom_1.jpg`

---

## 🧪 Chạy Kiểm Thử (Unit Tests)

Chạy toàn bộ các test suites:
```powershell
pytest backend/tests/ -v
```

---

## 🌐 Hướng Dẫn Deploy Render & Cấu Hình Fanpage Facebook

### 1. Triển khai lên Render (Web Service)
1. Tạo Web Service mới trên [Render](https://render.com).
2. Thiết lập:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`
3. Cài đặt các **Environment Variables**:
   - `USE_LOCAL_LLM`: `false`
   - `OPENAI_API_KEY`: `sk-proj-...`
   - `OPENAI_MODEL`: `gpt-4o-mini`
   - `FB_PAGE_ACCESS_TOKEN`: `EAAB...` (Token lấy từ Fanpage Facebook)
   - `FB_VERIFY_TOKEN`: `fitman_webhook_verify_2026`
   - `SERVER_BASE_URL`: `https://ten-app-cua-ban.onrender.com`

### 2. Cấu hình Webhook trên Facebook Developers
1. Vào ứng dụng Facebook App > **Messenger** > **Settings** > **Webhooks**.
2. Nhấn **Callback URL**: `https://ten-app-cua-ban.onrender.com/webhook`
3. Nhập **Verify Token**: `fitman_webhook_verify_2026` (trùng với `FB_VERIFY_TOKEN`).
4. Đăng ký nhận sự kiện `messages` và `messaging_postbacks` cho Fanpage FITMAN.
