import os
import json
import asyncio
import logging
from typing import List, Dict, Optional, Any
import httpx
from app.config import settings
from app.prompts.system_prompt import get_system_prompt
from app.tools.schemas import FITMAN_TOOLS, AVAILABLE_FUNCTIONS
from app.tools.business_rules import tim_anh_san_pham, ALL_ANH_QUAN, ALL_ANH_AO

logger = logging.getLogger(__name__)

async def generate_response(messages: List[Dict[str, Any]], user_message: str) -> Dict[str, Any]:
    # Chuẩn bị danh sách messages đầy đủ
    full_messages = [msg.copy() for msg in messages]
    if not full_messages or full_messages[0].get("role") != "system":
        full_messages.insert(0, {"role": "system", "content": get_system_prompt()})

    full_messages.append({"role": "user", "content": user_message})

    # Xác định endpoint và header
    if settings.USE_LOCAL_LLM or not settings.OPENAI_API_KEY:
        api_url = f"{settings.QWEN_API_BASE.rstrip('/')}/chat/completions"
        model_name = "koboldcpp/Qwen3-Coder-30B-A3B-Instruct-Q3_K_M"
        headers = {"Content-Type": "application/json"}
    else:
        api_url = "https://api.openai.com/v1/chat/completions"
        model_name = settings.OPENAI_MODEL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
        }

    tool_calls_made = []
    reply_text = ""
    suggested_images: List[str] = []

    # Gọi LLM lần 1 (cho phép gọi tool)
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            res = await client.post(
                api_url,
                json={
                    "model": model_name,
                    "messages": full_messages,
                    "tools": FITMAN_TOOLS,
                    "tool_choice": "auto"
                },
                headers=headers
            )
            res.raise_for_status()
            res_data = res.json()
        except Exception as e:
            logger.warning(f"Error calling primary LLM at {api_url}: {e}. Trying fallback port...")
            fallback_url = f"http://127.0.0.1:{settings.QWEN_FALLBACK_PORT}/v1/chat/completions"
            try:
                res = await client.post(
                    fallback_url,
                    json={
                        "model": model_name,
                        "messages": full_messages,
                        "tools": FITMAN_TOOLS,
                        "tool_choice": "auto"
                    },
                    headers={"Content-Type": "application/json"}
                )
                res.raise_for_status()
                res_data = res.json()
            except Exception as fb_err:
                logger.error(f"Fallback LLM call failed: {fb_err}")
                return {
                    "reply_text": "Dạ em chào anh! Hiện tại hệ thống đang bận một chút, anh vui lòng để lại lời nhắn em hỗ trợ ngay nhé ạ!",
                    "tool_calls_made": [],
                    "suggested_image": None,
                    "suggested_images": [],
                    "updated_messages": full_messages
                }

        # Xử lý kết quả trả về
        assistant_msg = res_data["choices"][0]["message"]
        tool_calls = assistant_msg.get("tool_calls")

        if tool_calls:
            full_messages.append(assistant_msg)
            for tc in tool_calls:
                f_name = tc.get("function", {}).get("name")
                f_args_raw = tc.get("function", {}).get("arguments", "{}")
                if isinstance(f_args_raw, str):
                    try:
                        f_args = json.loads(f_args_raw)
                    except Exception:
                        f_args = {}
                else:
                    f_args = f_args_raw

                tool_calls_made.append(f_name)
                tool_result = {}

                if f_name in AVAILABLE_FUNCTIONS:
                    func = AVAILABLE_FUNCTIONS[f_name]
                    try:
                        if asyncio.iscoroutinefunction(func):
                            tool_result = await func(**f_args)
                        else:
                            tool_result = func(**f_args)
                        
                        # Nếu tool trả về image_urls hoặc image_url
                        if isinstance(tool_result, dict):
                            if tool_result.get("image_urls"):
                                for img in tool_result["image_urls"]:
                                    if img not in suggested_images:
                                        suggested_images.append(img)
                            elif tool_result.get("image_url"):
                                if tool_result["image_url"] not in suggested_images:
                                    suggested_images.append(tool_result["image_url"])
                    except Exception as err:
                        tool_result = {"error": str(err)}
                else:
                    tool_result = {"error": f"Tool {f_name} không tồn tại."}

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", "call_1"),
                    "name": f_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            # Gọi LLM lần 2 để tổng hợp câu trả lời tự nhiên
            try:
                final_res = await client.post(
                    api_url,
                    json={
                        "model": model_name,
                        "messages": full_messages
                    },
                    headers=headers
                )
                final_res.raise_for_status()
                final_msg = final_res.json()["choices"][0]["message"]
                full_messages.append(final_msg)
                reply_text = final_msg.get("content", "")
            except Exception as err2:
                logger.error(f"Error in second LLM call: {err2}")
                if "tinh_size" in tool_calls_made:
                    reply_text = f"Dạ số đo của anh chuẩn nhất là Size {tool_result.get('size', 'M')} nha anh. {tool_result.get('ly_do', '')}."
                elif "tinh_gia" in tool_calls_made:
                    reply_text = f"Dạ {tool_result.get('so_luong')} món của anh tổng tiền là {tool_result.get('tong_tien_format', '')} ({'Freeship' if tool_result.get('freeship') else 'Phí ship 30k'}) ạ!"
                else:
                    reply_text = "Dạ Fitman đã nhận được thông tin từ anh rồi ạ!"
        else:
            full_messages.append(assistant_msg)
            reply_text = assistant_msg.get("content", "")

    # Phân tích và bổ sung đề xuất ảnh đính kèm
    lower_user = user_message.lower()
    
    # Nếu hỏi chung về quần (mà chưa có đủ các ảnh quần)
    if any(k in lower_user for k in ["xem ảnh quần", "ảnh quần", "mẫu quần", "xem mẫu quần"]):
        for q_img in ALL_ANH_QUAN:
            if q_img not in suggested_images:
                suggested_images.append(q_img)

    # Nếu hỏi chung về áo (mà chưa có đủ các ảnh áo)
    elif any(k in lower_user for k in ["xem ảnh áo", "ảnh áo", "mẫu áo", "xem mẫu áo", "cac mau ao", "các mẫu áo"]):
        for a_img in ALL_ANH_AO:
            if a_img not in suggested_images:
                suggested_images.append(a_img)

    # Nếu chưa có ảnh nào từ trước, tự động tra cứu từ câu chat
    if not suggested_images:
        lookup_result = tim_anh_san_pham(user_message)
        if lookup_result.get("found"):
            suggested_images = lookup_result.get("image_urls", [])
        elif "tinh_size" in tool_calls_made:
            suggested_images = ["/static/products/bang_size.jpg"]

    suggested_image = suggested_images[0] if suggested_images else None

    return {
        "reply_text": reply_text,
        "tool_calls_made": tool_calls_made,
        "suggested_image": suggested_image,
        "suggested_images": suggested_images,
        "updated_messages": full_messages
    }
