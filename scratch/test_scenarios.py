import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.services.llm_service import generate_response
from app.tools.business_rules import chuan_hoa_ma_quan, tim_anh_san_pham

async def run_tests():
    output_lines = []
    def log(s):
        output_lines.append(s)
        # Safe print for Windows console
        try:
            print(s)
        except Exception:
            print(s.encode("ascii", "replace").decode("ascii"))

    log("="*60)
    log("TEST 1: UNIT TEST CHUẨN HÓA MÃ QUẦN")
    log("="*60)
    test_cases = [
        ("lấy tôi áo 30 31 quần 124 đi shop", "lấy tôi áo 30 31 quần 1, 2, 4 đi shop"),
        ("quần 12", "quần 1, 2"),
        ("quần 134", "quần 1, 3, 4"),
        ("quần 24", "quần 2, 4"),
        ("quần 1234", "quần 1, 2, 3, 4"),
        ("q124", "quần 1, 2, 4"),
        ("Q124", "quần 1, 2, 4"),
        ("quan 12", "quần 1, 2"),
        ("0794763225", "0794763225"),
        ("áo 30 31", "áo 30 31"),
    ]
    for inp, exp in test_cases:
        res = chuan_hoa_ma_quan(inp)
        passed = (res == exp)
        log(f"Input: {inp} -> {res} | {'PASS' if passed else 'FAIL'}")

    log("\n" + "="*60)
    log("TEST 2: SCENARIO 1 (ẢNH 1 - ĐẶT ÁO 30 31 QUẦN 124)")
    log("="*60)
    user_msg_1 = "lấy tôi áo 30 31 quần 124 đi shop"
    res1 = await generate_response([], user_msg_1)
    reply1 = res1.get("reply_text", "")
    log(f"User: {user_msg_1}")
    log(f"Bot reply:\n{reply1}\n")

    # Kiểm tra:
    # 1. Không chứa "124" hoặc "mẫu 124"
    # 2. Phải có 5 món hoặc liệt kê mẫu 1, 2, 4
    # 3. Phải hỏi chiều cao cân nặng
    has_wrong_124 = "mẫu 124" in reply1.lower() or "124" in reply1.replace("0794763225", "")
    has_size_ask = any(k in reply1.lower() for k in ["chiều cao", "cân nặng", "size", "số đo"])
    log(f"Check 1: Không chứa 'mẫu 124': {'PASS' if not has_wrong_124 else 'FAIL'}")
    log(f"Check 2: Hỏi chiều cao cân nặng: {'PASS' if has_size_ask else 'FAIL'}")

    log("\n" + "="*60)
    log("TEST 3: SCENARIO 2 (ẢNH 2 - GỬI SĐT KHI CHƯA CÓ ĐỊA CHỈ)")
    log("="*60)
    # Tiếp tục hội thoại từ res1
    history = res1.get("updated_messages", [])
    # Khách cho số đo
    user_msg_2 = "cao 1m70 nặng 70kg"
    res2 = await generate_response(history, user_msg_2)
    history2 = res2.get("updated_messages", [])
    log(f"User: {user_msg_2}")
    log(f"Bot reply:\n{res2.get('reply_text', '')}\n")

    # Khách CHỈ GỬI SĐT (chưa có địa chỉ)
    user_msg_3 = "0794763225"
    res3 = await generate_response(history2, user_msg_3)
    reply3 = res3.get("reply_text", "")
    log(f"User: {user_msg_3}")
    log(f"Bot reply:\n{reply3}\n")

    # Kiểm tra:
    # 1. KHÔNG được nói "Ship tới địa chỉ bạn đã cung cấp"
    # 2. KHÔNG được nói "cảm ơn bạn đã ủng hộ shop" / chốt đơn hoàn tất
    # 3. PHẢI hỏi xin địa chỉ nhận hàng
    has_fake_address = "địa chỉ bạn đã cung cấp" in reply3.lower() or "địa chỉ bạn cung cấp" in reply3.lower()
    has_asked_address = any(k in reply3.lower() for k in ["địa chỉ", "dia chi", "nơi nhận", "giao đến đâu"])
    has_early_thanks = "cảm ơn bạn đã ủng hộ" in reply3.lower() or "cảm ơn anh đã ủng hộ" in reply3.lower()

    log(f"Check 1: Không bịa 'địa chỉ bạn đã cung cấp': {'PASS' if not has_fake_address else 'FAIL'}")
    log(f"Check 2: Không cảm ơn/chốt đơn sớm: {'PASS' if not has_early_thanks else 'FAIL'}")
    log(f"Check 3: Có hỏi xin địa chỉ giao hàng: {'PASS' if has_asked_address else 'FAIL'}")

    with open("scratch/test_scenarios_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

if __name__ == "__main__":
    asyncio.run(run_tests())
