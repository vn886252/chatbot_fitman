import os
import sys
import re
import json
import httpx
from typing import Dict, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

QWEN_ENDPOINT = os.getenv("QWEN_API_BASE", "http://127.0.0.1:5001/v1")
MODEL_NAME = "koboldcpp/Qwen3-Coder-30B-A3B-Instruct-Q3_K_M"

def check_health() -> bool:
    """Kiểm tra kết nối tới local Qwen AI server"""
    try:
        url = f"{QWEN_ENDPOINT.rstrip('/')}/models"
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return True
    except Exception as e:
        print(f"[ERROR] Cannot connect to local Qwen at {QWEN_ENDPOINT}: {e}")
    return False

def ask_qwen(prompt: str, system_context: str = "", max_tokens: int = 2048) -> str:
    """Gửi yêu cầu viết code đến Qwen 3 Coder (Coder chuyên trách)"""
    messages = []
    if system_context:
        messages.append({"role": "system", "content": system_context})
    messages.append({"role": "user", "content": prompt})

    url = f"{QWEN_ENDPOINT.rstrip('/')}/chat/completions"
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.1
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Bridge Error] {e}"

def delegate_coder_write_file(file_path: str, specification: str, existing_code: str = "") -> str:
    """
    Kỹ sư trưởng Antigravity giao việc cho Qwen 3 Coder viết mã nguồn cho 1 file cụ thể.
    """
    system_prompt = (
        "Bạn là Qwen 3 Coder - Coder chuyên trách trong dự án FITMAN Chatbot. "
        "Nhiệm vụ của bạn là viết mã nguồn Python / JSON chất lượng cao, đúng 100% đặc tả kỹ thuật từ Kỹ sư trưởng Antigravity. "
        "Mã nguồn phải chuẩn PEP 8, có type hint, docstring và xử lý lỗi chặt chẽ. "
        "Chỉ trả về khối mã nguồn hoàn chỉnh trong block ```python ... ``` hoặc ```json ... ```."
    )
    prompt = f"Yêu cầu viết file: `{file_path}`\n\nĐẶC TẢ KỸ THUẬT:\n{specification}\n"
    if existing_code:
        prompt += f"\nMÃ NGUỒN HIỆN TẠI ĐỂ THAM KHẢO/CẢI TIẾN:\n```python\n{existing_code}\n```\n"

    raw_output = ask_qwen(prompt, system_context=system_prompt, max_tokens=3000)
    
    # Trích xuất block code
    match = re.search(r"```(?:python|json)?\s*\n(.*?)\n```", raw_output, re.DOTALL)
    if match:
        return match.group(1)
    return raw_output

def delegate_coder_review_file(file_path: str, code_content: str) -> str:
    """
    Kỹ sư trưởng Antigravity giao việc cho Qwen 3 Coder review mã nguồn đã viết.
    """
    system_prompt = (
        "Bạn là Qwen 3 Coder. Hãy review chi tiết đoạn code sau về tính chính xác của logic nghiệp vụ, "
        "type hints, bảo mật và hiệu năng."
    )
    prompt = f"File cần review: `{file_path}`\n\n```python\n{code_content}\n```\n"
    return ask_qwen(prompt, system_context=system_prompt, max_tokens=1500)

if __name__ == "__main__":
    print(f"=== FITMAN Project: AI Role Delegation ===")
    print(f"- Lead Engineer & Architect: Antigravity")
    print(f"- Dedicated Local Coder: Qwen 3 Coder @ {QWEN_ENDPOINT}")
    print(f"- Customer Chatbot Engine: OpenAI GPT-4o-mini")
    print("-" * 50)
    if check_health():
        print("[SUCCESS] Local Qwen 3 Coder is active and ready to code!")
        test_msg = ask_qwen("Hãy xác nhận vai trò coder của bạn trong dự án FITMAN trong 1 câu ngắn.", max_tokens=80)
        print(f"[QWEN CONFIRMATION]:\n{test_msg.strip()}")
    else:
        print("[WARNING] Local Qwen server not found on port 5001.")
