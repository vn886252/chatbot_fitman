import sys
import os
sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(encoding='utf-8')
import asyncio
from app.services.llm_service import generate_response

async def run_tests():
    print("=== TEST 1: Khách đặt mẫu nhưng chưa có size ===")
    res1 = await generate_response([], "lấy a áo 1 3 4 quần 123")
    print("Bot reply:")
    print(res1["reply_text"])
    print("Tools called:", res1["tool_calls_made"])
    print()

    print("=== TEST 2: Khách hỏi giá mẫu mới ===")
    res2 = await generate_response([], "mẫu mới giá sao shop")
    print("Bot reply:")
    print(res2["reply_text"])
    print("Tools called:", res2["tool_calls_made"])
    print()

if __name__ == "__main__":
    asyncio.run(run_tests())
