import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.services.llm_service import generate_response
from app.services.telegram_service import send_daily_revenue_report
from app.services.order_service import get_daily_summary

async def run_tests():
    output = []
    def log(s):
        output.append(s)
        try:
            print(s)
        except Exception:
            print(s.encode("ascii", "replace").decode("ascii"))

    log("="*60)
    log("TEST 1: KHÁCH ĐẶT HÀNG NHƯNG CHƯA CÓ MÃ CỤ THỂ (CHỈ NÓI 2 ÁO)")
    log("="*60)
    msg_1a = "Lấy cho anh 2 cái áo size L ship về 123 Lê Lợi, SĐT 0901234567"
    res_1a = await generate_response([], msg_1a, customer_name="Anh Nam")
    reply_1a = res_1a.get("reply_text", "")
    tools_1a = res_1a.get("tool_calls_made", [])
    suggested_imgs_1a = res_1a.get("suggested_images", [])
    log(f"User: {msg_1a}")
    log(f"Tools called: {tools_1a}")
    log(f"Suggested images: {suggested_imgs_1a}")
    log(f"Bot reply:\n{reply_1a}\n")

    # Kiểm tra:
    # 1. KHÔNG được gọi tao_don_hang
    # 2. KHÔNG được cảm ơn / chốt đơn hoàn tất
    # 3. Phải gợi ý xem ảnh mẫu áo hoặc hỏi chọn mẫu
    chot_don_1a = "tao_don_hang" in tools_1a or "em cảm ơn anh đã ủng hộ" in reply_1a.lower()
    has_ask_mau_1a = any(k in reply_1a.lower() for k in ["chọn mẫu", "mẫu số", "mẫu nào", "mẫu áo", "xem mẫu", "gửi anh"])
    log(f"Check 1: KHÔNG chốt đơn khi chưa có mã cụ thể: {'PASS' if not chot_don_1a else 'FAIL'}")
    log(f"Check 2: Có gửi ảnh/bảo khách chọn mẫu áo: {'PASS' if has_ask_mau_1a or bool(suggested_imgs_1a) else 'FAIL'}")

    log("\n" + "="*60)
    log("TEST 2: KHÁCH ĐẶT CHUNG CHUNG KHÔNG RÕ ÁO HAY QUẦN ('Lấy tôi 3 cái')")
    log("="*60)
    msg_1b = "Lấy tôi 3 cái đi shop"
    res_1b = await generate_response([], msg_1b)
    reply_1b = res_1b.get("reply_text", "")
    tools_1b = res_1b.get("tool_calls_made", [])
    log(f"User: {msg_1b}")
    log(f"Bot reply:\n{reply_1b}\n")
    chot_don_1b = "tao_don_hang" in tools_1b
    has_ask_category = any(k in reply_1b.lower() for k in ["áo hay quần", "áo", "quần", "mẫu"])
    log(f"Check 1: KHÔNG chốt đơn: {'PASS' if not chot_don_1b else 'FAIL'}")
    log(f"Check 2: Có hỏi/gợi ý áo hoặc quần để chọn mẫu: {'PASS' if has_ask_category else 'FAIL'}")

    log("\n" + "="*60)
    log("TEST 3: ĐẶT HÀNG ĐẦY ĐỦ 4 YẾU TỐ -> TẠO ĐƠN & BẮN TELEGRAM")
    log("="*60)
    # Bước 1: Khách đặt hàng có mã cụ thể
    msg_3a = "lấy tôi áo 30 31 quần 124 đi shop"
    res_3a = await generate_response([], msg_3a, customer_name="Nguyễn Văn Tuấn", sender_id="fb_user_12345")
    hist_3a = res_3a.get("updated_messages", [])
    log(f"User: {msg_3a}")
    log(f"Bot reply: {res_3a.get('reply_text', '')}\n")

    # Bước 2: Khách cho số đo
    msg_3b = "cao 1m70 nặng 70kg"
    res_3b = await generate_response(hist_3a, msg_3b, customer_name="Nguyễn Văn Tuấn", sender_id="fb_user_12345")
    hist_3b = res_3b.get("updated_messages", [])
    log(f"User: {msg_3b}")
    log(f"Bot reply: {res_3b.get('reply_text', '')}\n")

    # Bước 3: Khách cho đủ SĐT và địa chỉ
    msg_3c = "SĐT 0794763225, ship tới 27 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM nha shop"
    res_3c = await generate_response(hist_3b, msg_3c, customer_name="Nguyễn Văn Tuấn", sender_id="fb_user_12345")
    reply_3c = res_3c.get("reply_text", "")
    tools_3c = res_3c.get("tool_calls_made", [])
    log(f"User: {msg_3c}")
    log(f"Tools called: {tools_3c}")
    log(f"Bot reply:\n{reply_3c}\n")

    log(f"Check 1: Đã gọi tool tao_don_hang: {'PASS' if 'tao_don_hang' in tools_3c else 'FAIL'}")
    summary_today = get_daily_summary()
    log(f"Check 2: Đơn đã lưu vào orders.json: {'PASS' if summary_today['total_orders'] > 0 else 'FAIL'}")
    log(f"Total orders today: {summary_today['total_orders']}, Total revenue: {summary_today['total_revenue']:,}đ")

    log("\n" + "="*60)
    log("TEST 4: TỔNG KẾT DOANH THU NGÀY VÀ GỬI TELEGRAM")
    log("="*60)
    report_sent = await send_daily_revenue_report()
    log(f"Check: Báo cáo doanh thu gửi Telegram thành công: {'PASS' if report_sent else 'FAIL'}")

    with open("scratch/test_new_requirements_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    asyncio.run(run_tests())
