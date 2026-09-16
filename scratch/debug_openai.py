import sys
import os
sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(encoding='utf-8')
import asyncio
from app.services.llm_service import generate_response

async def debug_call():
    # Giả lập các tin nhắn mà user vừa chat
    # Case A: User chat "lấy a áo 1 3 4 quần 123"
    print("--- Test A: lấy a áo 1 3 4 quần 123 ---")
    r1 = await generate_response([], "lấy a áo 1 3 4 quần 123")
    print("Bot:\n", r1["reply_text"])
    
    # Case B: Nếu tiếp theo user chat gì đó khiến bot ra câu trên
    # Thử giả lập bot hỏi và user trả lời
    history = [
        {"role": "user", "content": "lấy a áo 1 3 4 quần 123"},
        {"role": "assistant", "content": r1["reply_text"]}
    ]
    
    print("\n--- Test B1: User nói 'tôi lấy 6 món đó chốt đơn đi' ---")
    r2 = await generate_response(history, "tôi lấy 6 món đó chốt đơn đi")
    print("Bot:\n", r2["reply_text"])

    print("\n--- Test B2: User nói 'size M' ---")
    r3 = await generate_response(history, "size M")
    print("Bot:\n", r3["reply_text"])

if __name__ == "__main__":
    asyncio.run(debug_call())
