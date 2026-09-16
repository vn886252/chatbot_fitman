import sys, os
sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(encoding='utf-8')
import asyncio
from app.services.llm_service import generate_response

async def run_tests():
    print("====================================================")
    print("TEST 1: Khách nói 'Cho xem mẫu'")
    print("====================================================")
    r1 = await generate_response([], "Cho xem mẫu")
    print("Bot reply:", r1["reply_text"])
    print("Images returned:", len(r1["suggested_images"]), r1["suggested_images"])
    print()

    print("====================================================")
    print("TEST 2: Khách đặt 'Lấy áo 46 47 quần 123'")
    print("====================================================")
    r2 = await generate_response([], "Lấy áo 46 47 quần 123")
    print("Bot reply:\n", r2["reply_text"])
    print("Images returned:", len(r2["suggested_images"]))
    print()

    print("====================================================")
    print("TEST 3: Khách nói 'Ok chốt' khi chưa có size")
    print("====================================================")
    h_chot = [
        {"role": "user", "content": "Lấy áo 46 47 quần 123"},
        {"role": "assistant", "content": r2["reply_text"]}
    ]
    r3 = await generate_response(h_chot, "Ok chốt")
    print("Bot reply:\n", r3["reply_text"])
    print("Images returned (should be 0 - NO size chart spam!):", len(r3["suggested_images"]))
    print()

    print("====================================================")
    print("TEST 4: Khách cho số đo và địa chỉ, NHƯNG CHƯA CHO SĐT")
    print("====================================================")
    h_step4 = [
        {"role": "user", "content": "Lấy áo 46 47 quần 123"},
        {"role": "assistant", "content": r2["reply_text"]},
        {"role": "user", "content": "anh 1m7 nặng 72kg, ship tới 27 Lê Lợi P6 nha"}
    ]
    r4 = await generate_response(h_step4, "anh 1m7 nặng 72kg, ship tới 27 Lê Lợi P6 nha")
    print("Bot reply:\n", r4["reply_text"])
    print("Images returned:", len(r4["suggested_images"]))
    print()

    print("====================================================")
    print("TEST 5: Khách gửi SĐT thật 0794763225")
    print("====================================================")
    h_step5 = [
        {"role": "user", "content": "Lấy áo 46 47 quần 123"},
        {"role": "assistant", "content": r2["reply_text"]},
        {"role": "user", "content": "anh 1m7 nặng 72kg, ship tới 27 Lê Lợi P6 nha"},
        {"role": "assistant", "content": r4["reply_text"]}
    ]
    r5 = await generate_response(h_step5, "sđt anh là 0794763225")
    print("Bot reply:\n", r5["reply_text"])
    print("====================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
