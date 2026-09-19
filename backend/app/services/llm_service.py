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
from app.services.customer_service import get_customer_profile, format_customer_memory_context, save_customer_profile

logger = logging.getLogger(__name__)

async def generate_response(
    messages: List[Dict[str, Any]],
    user_message: str,
    customer_name: Optional[str] = None,
    sender_id: Optional[str] = None
) -> Dict[str, Any]:
    # Chuẩn hóa tiền xử lý mã quần dính liền (ví dụ: 'quần 124' -> 'quần 1, 2, 4')
    normalized_user_message = chuan_hoa_ma_quan(user_message)

    customer_profile = get_customer_profile(sender_id) if sender_id else None

    # Chuẩn bị danh sách messages đầy đủ
    full_messages = [msg.copy() for msg in messages]
    if not full_messages or full_messages[0].get("role") != "system":
        sys_prompt = get_system_prompt()
        if customer_name and customer_name != "Khách hàng":
            sys_prompt += f"\n\nLƯU Ý: Tên của khách hàng đang chat là: {customer_name}. Khi gọi tao_don_hang hãy điền ten_khach_hang='{customer_name}'."
        if customer_profile:
            memory_prompt = format_customer_memory_context(customer_profile)
            if memory_prompt:
                sys_prompt += f"\n\n{memory_prompt}"
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
                        # Chống bịa SĐT: Kiểm tra xem SĐT có thật sự do người dùng nhắn hay trùng với hồ sơ cũ
                        user_messages_text = " ".join([m.get("content", "") for m in full_messages if m.get("role") == "user"])
                        clean_passed_phone = re.sub(r'\D', '', str(f_args.get("so_dien_thoai") or ""))
                        all_user_digits = re.sub(r'\D', '', user_messages_text)

                        saved_phone = re.sub(r'\D', '', str(customer_profile.get("so_dien_thoai") or "")) if customer_profile else ""
                        saved_addr = str(customer_profile.get("dia_chi") or "").strip().lower() if customer_profile else ""
                        is_using_saved_phone = bool(saved_phone and clean_passed_phone == saved_phone)

                        if len(clean_passed_phone) < 10 or (clean_passed_phone not in all_user_digits and not is_using_saved_phone):
                            tool_calls_made.append(f_name)
                            tool_result = {
                                "success": False,
                                "error": "Khách hàng CHƯA cung cấp số điện thoại này trong tin nhắn! Bạn đang tự bịa SĐT. Tuyệt đối CẤM tạo đơn khi khách chưa gửi SĐT, hãy hỏi khách số điện thoại nhận hàng trước!"
                            }
                            full_messages.append({
                                "role": "tool",
                                "tool_call_id": tc.get("id", f"call_{turn}_{f_name}"),
                                "name": f_name,
                                "content": json.dumps(tool_result, ensure_ascii=False)
                            })
                            continue

                        # Chống bịa Địa chỉ: Kiểm tra xem địa chỉ có được khách nhắn trong tin nhắn hay trùng với hồ sơ cũ
                        passed_addr = str(f_args.get("dia_chi") or "").strip()
                        addr_tokens = [t.lower() for t in re.findall(r'[\w\d]+', passed_addr) if len(t) >= 3 and t.lower() not in ["quận", "huyện", "phường", "đường", "tỉnh", "thành", "phố", "tphcm", "hcm", "vietnam"]]
                        has_addr_match = any(t in user_messages_text.lower() for t in addr_tokens)
                        is_using_saved_addr = bool(saved_addr and (passed_addr.lower() in saved_addr or saved_addr in passed_addr.lower()))

                        if not has_addr_match and not is_using_saved_addr and not any(k in user_messages_text.lower() for k in ["giao", "ship", "địa chỉ", "nhận", "nhà", "cũ", "chỗ cũ"]):
                            tool_calls_made.append(f_name)
                            tool_result = {
                                "success": False,
                                "error": "Khách hàng CHƯA cung cấp địa chỉ giao hàng này trong tin nhắn! Bạn đang tự bịa địa chỉ. Tuyệt đối CẤM tạo đơn khi khách chưa gửi địa chỉ, hãy hỏi khách địa chỉ nhận hàng cụ thể trước!"
                            }
                            full_messages.append({
                                "role": "tool",
                                "tool_call_id": tc.get("id", f"call_{turn}_{f_name}"),
                                "name": f_name,
                                "content": json.dumps(tool_result, ensure_ascii=False)
                            })
                            continue

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

                            # Tự động lưu hồ sơ khách hàng khi tính size
                            if f_name == "tinh_size" and sender_id and isinstance(tool_result, dict):
                                try:
                                    sz = tool_result.get("size", "")
                                    ao_m = re.search(r'Áo\s*([SMLXL]+)', sz, re.IGNORECASE)
                                    quan_m = re.search(r'Quần\s*([SMLXL]+)', sz, re.IGNORECASE)
                                    kw = {
                                        "chieu_cao": tool_result.get("chieu_cao"),
                                        "can_nang": tool_result.get("can_nang")
                                    }
                                    if ao_m:
                                        kw["size_ao"] = ao_m.group(1).upper()
                                    if quan_m:
                                        kw["size_quan"] = quan_m.group(1).upper()
                                    save_customer_profile(sender_id, **kw)
                                except Exception as ex:
                                    logger.warning(f"Error saving customer size profile: {ex}")

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
        # Nếu hỏi xem mẫu mới (tối đa 6 mẫu mới nhất)
        is_new_query = (
            any(k in lower_user for k in ["mẫu mới", "mau moi", "2026", "hàng mới", "hang moi", "mới về", "moi ve", "mới nhất", "moi nhat"])
            or (bool(re.search(r'\bnew\b', lower_user)) and not bool(re.search(r'\bnew_\d+\b', lower_user)))
        )
        if is_new_query:
            try:
                from app.services.new_models_service import get_new_models
                new_m = get_new_models()
                for m in new_m:
                    img = m.get("image_url")
                    if img and img not in suggested_images:
                        suggested_images.append(img)
            except Exception:
                pass
            if not suggested_images:
                for img in ALL_ANH_AO + ALL_ANH_QUAN:
                    if img not in suggested_images:
                        suggested_images.append(img)

        # Nếu hỏi xem mẫu cũ
        elif any(k in lower_user for k in ["mẫu cũ", "mau cu", "mẫu trước", "mau truoc"]):
            for img in ALL_ANH_AO + ALL_ANH_QUAN:
                if img not in suggested_images:
                    suggested_images.append(img)
            try:
                from app.services.new_models_service import get_old_models
                for m in get_old_models():
                    img = m.get("image_url")
                    if img and img not in suggested_images:
                        suggested_images.append(img)
            except Exception:
                pass

        # Nếu hỏi xem tất cả (cả áo lẫn quần) hoặc xem mẫu chung
        elif any(k in lower_user for k in ["tất cả", "tat ca", "hết", "het", "xem hết", "all", "cho xem mẫu", "xem mẫu", "mẫu đâu", "xem mau", "cho xem mau"]):
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

    suggested_image = suggested_images[0] if suggested_images else None

    return {
        "reply_text": reply_text,
        "tool_calls_made": tool_calls_made,
        "suggested_image": suggested_image,
        "suggested_images": suggested_images,
        "updated_messages": full_messages
    }
