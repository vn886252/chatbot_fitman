# 🎬 HỆ THỐNG MARKETING AUTOMATION (TELEGRAM + COMFYUI MINIMAX H3)

Hệ thống tự động hóa toàn diện từ ảnh sản phẩm đến video thương mại 15s - 30s chất lượng cao:
1. **Tiếp nhận ảnh sản phẩm** qua Telegram Bot.
2. **Vision AI Agent** tự động phân tích sản phẩm, soạn kịch bản 3 phân cảnh (Storyboard) và tạo Prompt kỹ thuật chuẩn 100% cú pháp MiniMax H3.
3. **Phê duyệt kịch bản (Human-in-the-loop):** Gửi kịch bản tiếng Việt lên Telegram để bạn đọc duyệt (`[✅ Duyệt & Tạo Video]` hoặc `[🔄 Viết lại]`).
4. **Tự động hóa ComfyUI:** Sau khi duyệt, hệ thống tự nạp ảnh vào Node `169` (`LoadImage`), bơm prompt vào Node `84` (`PrimitiveStringMultiline`), lắng nghe tiến độ render qua WebSocket và gửi file `.mp4` hoàn chỉnh trả về Telegram cho bạn!

---

## 📁 Cấu trúc thư mục

```
F:\project fitman\marketing\
├── minimax_h3_workflow.json  # Workflow ComfyUI MiniMax H3 gốc bạn cung cấp
├── config.py                 # File cấu hình biến môi trường và ComfyUI
├── workflow_api.py           # Bộ chuyển đổi UI -> API và giao tiếp ComfyUI qua WebSocket
├── llm_agent.py              # Vision AI Agent phân tích ảnh & viết kịch bản
├── bot_automation.py         # Main script chạy Telegram Bot
├── requirements.txt          # Thư viện Python cần thiết
├── .env.example              # Mẫu cấu hình API Keys
└── README.md                 # Hướng dẫn chi tiết
```

---

## 🚀 Hướng dẫn cài đặt và khởi chạy

### Bước 1: Cài đặt thư viện
Mở Terminal trong thư mục `F:\project fitman\marketing` và chạy:
```bash
pip install -r requirements.txt
```

### Bước 2: Điền API Keys
1. Sao chép file `.env.example` thành `.env`:
   ```bash
   copy .env.example .env
   ```
2. Mở file `.env` và điền:
   * `TELEGRAM_BOT_TOKEN`: Token lấy từ bot `@BotFather` trên Telegram.
   * `GEMINI_API_KEY`: API Key lấy từ Google AI Studio (miễn phí).
   * `COMFYUI_HOST`: `127.0.0.1` (nếu chạy cùng máy với ComfyUI).

### Bước 3: Khởi động ComfyUI
Mở ComfyUI trên máy tính của bạn (đảm bảo workflow MiniMax H3 đã có đủ model và custom node `VHS_VideoCombine`, `MiniMaxH3ReferenceToVideo`).

### Bước 4: Chạy Bot Automation
Trong thư mục `F:\project fitman\marketing`:
```bash
python bot_automation.py
```

### Bước 5: Trải nghiệm
* Mở Telegram nhắn tin cho Bot của bạn.
* Gửi 1 tấm ảnh sản phẩm (có thể kèm mô tả như *"Làm video phong cách sang trọng, hiện đại"*).
* Bot sẽ gửi lại kịch bản 3 phân cảnh tiếng Việt.
* Bạn bấm nút **"✅ Duyệt & Tạo Video Ngay"** $\rightarrow$ Hệ thống tự động kích hoạt ComfyUI render và gửi file video MP4 về lại cho bạn.
