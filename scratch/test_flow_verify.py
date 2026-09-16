import sys, os
sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(encoding='utf-8')
import asyncio
from app.services.llm_service import generate_response

async def run_test():
    history = []
    
    print("=== BƯỚC 1: Khách đặt 6 món nhưng chưa có size ===")
    r1 = await generate_response(history, "lấy a áo 1 3 4 quần 123")
    print("Bot:\n", r1["reply_text"])
    print("-" * 50)
    
    history.append({"role": "user", "content": "lấy a áo 1 3 4 quần 123"})
    history.append({"role": "assistant", "content": r1["reply_text"]})
    
    print("\n=== BƯỚC 2: Khách cho chiều cao cân nặng ===")
    r2 = await generate_response(history, "anh 1m7 nặng 72kg")
    print("Bot:\n", r2["reply_text"])
    print("-" * 50)
    
    history.append({"role": "user", "content": "anh 1m7 nặng 72kg"})
    history.append({"role": "assistant", "content": r2["reply_text"]})
    
    print("\n=== BƯỚC 3: Khách cho địa chỉ và số điện thoại ===")
    r3 = await generate_response(history, "giao về 123 Lê Lợi Q1 HCM, sđt 0901234567")
    print("Bot:\n", r3["reply_text"])
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(run_test())
