import sys
import os
sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(encoding='utf-8')
import asyncio
from app.services.llm_service import generate_response

async def run_flow():
    history = []
    
    print("--- Khách: lấy a áo 1 3 4 quần 123 ---")
    r1 = await generate_response(history, "lấy a áo 1 3 4 quần 123")
    print("Bot:\n", r1["reply_text"])
    print("Tools:", r1["tool_calls_made"])
    
    # Giả lập webhook lưu history (chỉ user + assistant text)
    history.append({"role": "user", "content": "lấy a áo 1 3 4 quần 123"})
    history.append({"role": "assistant", "content": r1["reply_text"]})
    
    print("\n--- Khách: anh 1m7 nặng 72kg ---")
    r2 = await generate_response(history, "anh 1m7 nặng 72kg")
    print("Bot:\n", r2["reply_text"])
    print("Tools:", r2["tool_calls_made"])
    
    history.append({"role": "user", "content": "anh 1m7 nặng 72kg"})
    history.append({"role": "assistant", "content": r2["reply_text"]})
    
    print("\n--- Khách: ship về 123 Lê Lợi Q1 HCM, sđt 0901234567 ---")
    r3 = await generate_response(history, "ship về 123 Lê Lợi Q1 HCM, sđt 0901234567")
    print("Bot:\n", r3["reply_text"])
    print("Tools:", r3["tool_calls_made"])

if __name__ == "__main__":
    asyncio.run(run_flow())
