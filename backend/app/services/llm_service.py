import os
import re
import json
import asyncio
import logging
from typing import List, Dict, Optional, Any
import httpx
from app.config import settings
from app.prompts.system_prompt import get_system_prompt
from app.tools.schemas import FITMAN_TOOLS, AVAILABLE_FUNCTIONS
from app.tools.business_rules import tim_anh_san_pham, ALL_ANH_QUAN, ALL_ANH_AO, chuan_hoa_ma_quan

logger = logging.getLogger(__name__)

async def generate_response(
    messages: List[Dict[str, Any]],
    user_message: str,
    customer_name: Optional[str] = None,
    sender_id: Optional[str] = None
) -> Dict[str, Any]:
    # Chuẩn hóa tiền xử lý mã quần dính liền (ví dụ: 'quần 124' -> 'quần 1, 2, 4')
    normalized_user_message = chuan_hoa_ma_quan(user_message)

    # Chuẩn bị danh sách messages đầy đủ
    full_messages = [msg.copy() for msg in messages]
    if not full_messages or full_messages[0].get("role") != "system":
        sys_prompt = get_system_prompt()
        if customer_name and customer_name != "Khách hàng":
            sys_prompt += f"\n\nLƯU Ý: Tên của khách hàng đang chat là: {customer_name}. Khi gọi tao_don_hang hãy điền ten_khach_hang='{customer_name}'."
        full_messages.insert(0, {"role": "system", "content": sys_prompt})

    full_messages.append({"role": "user", "content": normalized_user_message})

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

    # Multi-turn tool calling loop (tối đa 3 lượt)
    max_turns = 3
    async with httpx.AsyncClient(timeout=120.0) as client:
        for turn in range(max_turns):
            res_data = None
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
                    if not reply_text:
                        return {
                            "reply_text": "Dạ em chào anh! Hiện tại hệ thống đang bận một chút, anh vui lòng để lại lời nhắn em hỗ trợ ngay nhé ạ!",
                            "tool_calls_made": tool_calls_made,
                            "suggested_image": None,
                            "suggested_images": suggested_images,
                            "updated_messages": full_messages
                        }
                    break

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

                    if f_name == "tao_don_hang":
                        if customer_name and (not f_args.get("ten_khach_hang") or f_args.get("ten_khach_hang") == "Khách hàng"):
                            f_args["ten_khach_hang"] = customer_name
                        if sender_id and not f_args.get("sender_id"):
                            f_args["sender_id"] = sender_id

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
                        "tool_call_id": tc.get("id", f"call_{turn}_{f_name}"),
                        "name": f_name,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
                # Tiếp tục vòng lặp để LLM xử lý tiếp (có thể gọi tool khác hoặc trả lời văn bản)
            else:
                # LLM không gọi tool, trả về văn bản hoàn chỉnh
                full_messages.append(assistant_msg)
                reply_text = assistant_msg.get("content", "")
                break

        # Nếu sau max_turns vẫn chưa có reply_text (do mọi turn đều là tool call)
        if not reply_text:
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
            except Exception as final_err:
                logger.error(f"Error in final LLM response generation: {final_err}")
                if "tao_don_hang" in tool_calls_made:
                    reply_text = "Dạ Fitman đã lên đơn thành công cho anh rồi ạ! Cảm ơn anh đã ủng hộ shop! 💪"
                elif "tinh_size" in tool_calls_made:
                    reply_text = "Dạ em đã tư vấn size chuẩn cho mình rồi nha anh!"
                else:
                    reply_text = "Dạ Fitman đã ghi nhận thông tin của anh rồi ạ!"

    # Strip markdown image links khỏi reply_text (safety net - LLM đôi khi vẫn tự thêm)
    # Pattern: ![text](url) hoặc ![text]([url](url2))
    reply_text = re.sub(r'!\[.*?\]\(.*?\)', '', reply_text).strip()
    # Xóa markdown link thường [text](url) mà LLM có thể chèn
    reply_text = re.sub(r'\[([^\]]*)\]\((?:https?://)?\S+\)', r'\1', reply_text).strip()
    # Xóa dòng chỉ chứa khoảng trắng (space/tab) thành dòng trống thật
    reply_text = re.sub(r'(?m)^[ \t]+$', '', reply_text)
    # Gộp 2+ dòng trống liên tiếp thành 1 dòng trống duy nhất
    reply_text = re.sub(r'\n{2,}', '\n\n', reply_text).strip()

    # Bổ sung ảnh từ keyword trong câu chat (CHỈ KHI khách hỏi xem ảnh / xem mẫu)
    lower_user = user_message.lower()

    # KIỂM TRA: Nếu khách đang ĐẶT HÀNG có số / mã cụ thể (ví dụ: 'lấy áo 45 46 quần 13', 'áo 30 31 quần 124')
    # TUYỆT ĐỐI KHÔNG gửi ảnh fallback!
    has_order_verb = any(w in lower_user for w in ["lấy", "lay", "đặt", "dat", "mua", "chốt", "chot"])
    has_digits = bool(re.search(r'\d+', user_message))
    is_ordering_with_codes = has_order_verb and has_digits

    if not is_ordering_with_codes:
        # Nếu hỏi xem tất cả (cả áo lẫn quần) hoặc xem mẫu chung
        if any(k in lower_user for k in ["tất cả", "tat ca", "hết", "het", "xem hết", "all", "cho xem mẫu", "xem mẫu", "mẫu đâu", "xem mau", "cho xem mau", "mẫu mới", "mau moi"]):
            for img in ALL_ANH_AO + ALL_ANH_QUAN:
                if img not in suggested_images:
                    suggested_images.append(img)

        # Nếu hỏi xem ảnh quần
        elif any(k in lower_user for k in ["xem ảnh quần", "ảnh quần", "mẫu quần", "xem mẫu quần", "cac mau quan", "các mẫu quần", "cho xem quần", "xem quan"]):
            for q_img in ALL_ANH_QUAN:
                if q_img not in suggested_images:
                    suggested_images.append(q_img)

        # Nếu hỏi xem ảnh áo
        elif any(k in lower_user for k in ["xem ảnh áo", "ảnh áo", "mẫu áo", "xem mẫu áo", "cac mau ao", "các mẫu áo", "cho xem áo", "xem ao", "gửi áo"]):
            for a_img in ALL_ANH_AO:
                if a_img not in suggested_images:
                    suggested_images.append(a_img)

        # Chỉ gửi bảng size KHI khách hỏi bảng size (tránh spam ảnh size)
        elif any(k in lower_user for k in ["bảng size", "bang size", "size chart", "bảng số đo", "bang so do", "form size"]):
            if "/static/products/bang_size.jpg" not in suggested_images:
                suggested_images.append("/static/products/bang_size.jpg")

    # Safety net: Tự động ghi nhận đơn nếu bot đã xác nhận chốt đơn trong reply_text mà tool tao_don_hang chưa được gọi
    if "tao_don_hang" not in tool_calls_made:
        lower_reply = reply_text.lower()
        phone_match = re.search(r'0\d{9,10}', reply_text) or re.search(r'0\d{9,10}', user_message)
        has_shipping = any(k in lower_reply or k in lower_user for k in ["ship tới", "giao tới", "ship đến", "giao đến", "giao qua", "giao tại", "địa chỉ"])
        has_total = any(k in lower_reply for k in ["tổng", "freeship", "tổng cộng", "tiền"])
        has_thanks = any(k in lower_reply for k in ["cảm ơn", "ủng hộ shop", "tạo đơn", "lên đơn", "chốt đơn"])

        if phone_match and has_shipping and (has_total or has_thanks):
            logger.info("Safety net triggered: Auto-creating order from confirmed reply_text...")
            try:
                price_match = re.search(r'(\d{1,3}(?:\.\d{3})+|\d{2,4}\s*(?:k|000))', reply_text)
                extracted_price = 0
                if price_match:
                    raw_p = price_match.group(1).replace(".", "").lower()
                    if "k" in raw_p:
                        extracted_price = int(raw_p.replace("k", "").strip()) * 1000
                    else:
                        extracted_price = int(raw_p)

                # Trích xuất địa chỉ thực tế từ user_message hoặc reply_text
                dia_chi_text = ""
                addr_match = re.search(r'(?:ship tới|giao tới|giao đến|ship đến|giao qua|địa chỉ:?|dc:?)\s*\*?([^,\n\*\.\!]+(?:,[^,\n\*\.\!]+)*)', user_message, re.IGNORECASE)
                if not addr_match:
                    addr_match = re.search(r'(?:ship tới|giao tới|giao đến|ship đến|địa chỉ:?)\s*\*?([^\n\*]+)', reply_text, re.IGNORECASE)
                if addr_match:
                    dia_chi_text = addr_match.group(1).strip().rstrip(".,")

                # Lọc danh sách món hợp lệ
                items = []
                for line in reply_text.split("\n"):
                    line_clean = line.strip()
                    if (line_clean.startswith("-") or line_clean.startswith("•") or line_clean.startswith("+")) and not any(ign in line_clean.lower() for ign in ["sđt", "điện thoại", "địa chỉ", "giao", "ship", "size của anh", "size :"]):
                        items.append(line_clean.lstrip("-•+ ").strip())

                from app.tools.business_rules import tao_don_hang
                await tao_don_hang(
                    danh_sach_mon=items or ["Combo sản phẩm Fitman"],
                    so_luong=len(items) or 1,
                    tong_tien=extracted_price or 0,
                    so_dien_thoai=phone_match.group(0),
                    dia_chi=dia_chi_text or "Chưa có địa chỉ cụ thể",
                    ten_khach_hang=customer_name or "Khách hàng",
                    sender_id=sender_id or ""
                )
                tool_calls_made.append("tao_don_hang")
            except Exception as auto_order_err:
                logger.error(f"Error in auto-order safety net: {auto_order_err}")

    suggested_image = suggested_images[0] if suggested_images else None

    return {
        "reply_text": reply_text,
        "tool_calls_made": tool_calls_made,
        "suggested_image": suggested_image,
        "suggested_images": suggested_images,
        "updated_messages": full_messages
    }
