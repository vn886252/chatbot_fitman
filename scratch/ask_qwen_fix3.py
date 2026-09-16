import urllib.request
import json

PROMPT = """Bạn là chuyên gia thiết kế prompt cho Chatbot bán hàng thời trang nam (Fitman).
Bot vừa gặp 3 lỗi nghiêm trọng khi chat với khách:

1. LỖI 1: Khách báo chọn 6 món (3 áo: mẫu 1, 3, 4 và 3 quần: mẫu 1, 2, 3). Nhưng bot lại tự ý bớt xén còn 4 món: "2 áo size M (mẫu 1, mẫu 4) + 2 quần size M (mẫu 1, mẫu 2) tổng 530.000đ freeship".
-> Yêu cầu: Bot phải giữ đúng 100% số lượng và đúng các mẫu khách đã chọn. Khách chọn bao nhiêu món phải ghi nhận đủ bấy nhiêu món, tính tiền đúng số lượng đó, tuyệt đối không được tự ý bỏ bớt món hoặc đổi số lượng của khách!

2. LỖI 2: Khách chưa hề cho địa chỉ và số điện thoại, nhưng bot lại in ra câu:
"Ship tới địa chỉ của bạn, sđt số điện thoại của bạn giúp em với ạ! 📦 Em cảm ơn bạn đã ủng hộ shop 💪"
Lý do: Prompt có mẫu chốt đơn "Ship tới *[địa chỉ]*, sđt *[SĐT]*... Em cảm ơn anh đã ủng hộ shop", nên khi chưa có địa chỉ/sđt, bot thay placeholder bằng "địa chỉ của bạn" rồi cảm ơn như thật!
-> Yêu cầu: Phân tách rõ ràng các trạng thái:
- Khi ĐANG THIẾU địa chỉ / SĐT: CHỈ hỏi xin địa chỉ và SĐT nhẹ nhàng ("Anh cho em xin địa chỉ và số điện thoại để em lên đơn gửi cho mình nha! 📦"). CẤM in câu "Ship tới..." và CẤM cảm ơn ủng hộ shop ở bước này!
- CHỈ KHI NÀO khách đã cung cấp địa chỉ cụ thể và SĐT cụ thể bằng số thì MỚI ĐƯỢC chốt đơn và cảm ơn!

3. LỖI 3: Khách chưa có size, bot lại không tư vấn size mà lại "bắt khách chọn size", hoặc tự ý gán size M cho tất cả các món!
-> Yêu cầu: Khách không có bảng size nên không thể tự chọn size. Bot BẮT BUỘC PHẢI CHỦ ĐỘNG HỎI: "Dạ anh cho em xin chiều cao và cân nặng để em tư vấn size chuẩn cho mình nha! 💪". CẤM bảo khách tự chọn size. CẤM tự ý gán size M khi chưa có số đo!

Hãy viết lại các quy tắc bằng tiếng Việt thật sắc bén, chặt chẽ, chia thành các điều luật rõ ràng và có ví dụ CẤM/ĐƯỢC LÀM để đưa vào System Prompt.
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
    with open("scratch/qwen_rules_out2.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Done! Length:", len(content))
except Exception as e:
    print("Error:", e)
