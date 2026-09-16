import sys, os
sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(encoding='utf-8')
import asyncio, json
from app.services.llm_service import generate_response

async def test_qwen_flow():
    # Thử giả lập tình huống user gặp
    print("--- Message 1 ---")
    r1 = await generate_response([], "lấy a áo 1 3 4 quần 123")
    print(r1["reply_text"])
    
    # Giả sử sau r1, user trả lời hoặc bot đã nói gì đó
    # Giả sử bot nói r1, sau đó user nhắn gì?
    # Nếu user nhắn: "chốt đơn cho tôi" hoặc "tôi lấy 6 món đó"
    h = [
        {"role": "user", "content": "lấy a áo 1 3 4 quần 123"},
        {"role": "assistant", "content": r1["reply_text"]}
    ]
    print("\n--- Message 2: user nhắn 'tôi lấy 6 món đó' ---")
    r2 = await generate_response(h, "tôi lấy 6 món đó")
    print(r2["reply_text"])

asyncio.run(test_qwen_flow())
