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


def extract_body_measurements_from_text(text: str) -> tuple[Optional[float], Optional[float]]:
    """
    Trích xuất cân nặng (kg) và chiều cao (m) từ tin nhắn.
    Hỗ trợ: '70kg', 'nặng 70kg', '1m60', 'cao 1m60', '1.60m', '165cm', 'cao 165', v.v.
    """
    if not text:
        return None, None
    kg_m = re.search(r'(?:(?:nặng|nang)\s*)?(\d{2,3}(?:\.\d+)?)\s*(?:kg|kí|ký|ki|cân|can)\b', text, re.IGNORECASE)
    if not kg_m:
        kg_m = re.search(r'(?:nặng|nang)\s*(\d{2,3}(?:\.\d+)?)\b', text, re.IGNORECASE)
    weight = float(kg_m.group(1)) if kg_m else None

    # Chiều cao: 1m60, 1m7, 1.70m, 170cm, cao 165
    h_m1 = re.search(r'\b1[mM](\d{1,2})\b', text)
    h_m2 = re.search(r'\b1\.\d{1,2}\s*m?\b', text)
    h_m3 = re.search(r'\b(1\d{2})\s*cm\b', text)
    h_m4 = re.search(r'(?:cao|chieu cao|chiều cao)\s*(1[4-9]\d)\b', text, re.IGNORECASE)

    height = None
    if h_m1:
        d = h_m1.group(1)
        d_str = d if len(d) == 2 else d + "0"
        height = float("1." + d_str)
    elif h_m2:
        height = float(re.sub(r'[^\d.]', '', h_m2.group(0)))
    elif h_m3:
        height = float(h_m3.group(1)) / 100.0
    elif h_m4:
        height = float(h_m4.group(1)) / 100.0

    return weight, height

async def generate_response(
    messages: List[Dict[str, Any]],
    user_message: str,
    customer_name: Optional[str] = None,
    sender_id: Optional[str] = None
) -> Dict[str, Any]:
    # Chuẩn hóa tiền xử lý mã quần dính liền (ví dụ: 'quần 124' -> 'quần 1, 2, 4')
    normalized_user_message = chuan_hoa_ma_quan(user_message)

    customer_profile = get_customer_profile(sender_id) if sender_id else None

    # Phát hiện số đo cơ thể và size từ customer_profile, lịch sử chat và tin nhắn hiện tại
    known_weight = customer_profile.get("can_nang") if customer_profile else None
    known_height = customer_profile.get("chieu_cao") if customer_profile else None
    known_size = customer_profile.get("size_ao") if customer_profile else None

    # Quét trong lịch sử chat và tin nhắn hiện tại
    all_turns = list(messages) + [{"role": "user", "content": normalized_user_message}]
    for m in all_turns:
        c = m.get("content", "")
        if c:
            w, h = extract_body_measurements_from_text(c)
            if w and not known_weight:
                known_weight = w
            if h and not known_height:
                known_height = h
            sz_m = re.search(r'(?:size|sz|mặc size)\s*\*{0,2}([SMLXL]+)\*{0,2}', c, re.IGNORECASE)
            if sz_m and not known_size:
                known_size = sz_m.group(1).upper()

    # Nếu có cân nặng mà chưa có size, tự động tính size
    if known_weight and not known_size:
        try:
            from app.tools.business_rules import tinh_size
            res_sz = tinh_size(known_weight, known_height)
            ao_m = re.search(r'Áo\s*([SMLXL]+)', res_sz.get("size", ""), re.IGNORECASE)
            if ao_m:
                known_size = ao_m.group(1).upper()
        except Exception:
            pass

    # Tự động cập nhật hồ sơ khách hàng nếu có số đo
    if sender_id and (known_weight or known_height or known_size):
        kw_prof = {}
        if known_weight:
            kw_prof["can_nang"] = known_weight
        if known_height:
            kw_prof["chieu_cao"] = known_height
        if known_size:
            kw_prof["size_ao"] = known_size
        try:
            save_customer_profile(sender_id, **kw_prof)
        except Exception as e:
            logger.warning(f"Error auto-saving customer profile: {e}")

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
        if known_weight or known_size:
            info_parts = []
            if known_weight:
                info_parts.append(f"{known_weight}kg")
            if known_height:
                info_parts.append(f"{known_height}m")
            if known_size:
                info_parts.append(f"Size {known_size}")
            info_str = ", ".join(info_parts)
            sys_prompt += (
                f"\n\n⚠️ LƯU Ý ĐẶC BIỆT VỀ KHÁCH NÀY:\n"
                f"- Khách ĐÃ CÓ thông tin số đo / size: {info_str}.\n"
                f"- ❌ TUYỆT ĐỐI CẤM hỏi lại 'chiều cao cân nặng'! CẤM hỏi câu 'cho em xin chiều cao và cân nặng'!\n"
                f"- ✅ BẮT BUỘC: Nhắc nhẹ size của khách (size {known_size or 'chuẩn'}) và hỏi MẪU khách thích hoặc THÔNG TIN GIAO HÀNG!"
            )
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
    async with httpx.AsyncClient(timeout=25.0) as client:
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
                logger.warning(f"Error calling primary LLM at {api_url}: {e}.")
                # Nếu dùng OpenAI (Render production), thử retry 1 lần sau 1.5s chống rớt mạng tạm thời
                if not settings.USE_LOCAL_LLM and settings.OPENAI_API_KEY:
                    try:
                        logger.info("Retrying OpenAI call once after 1.5s...")
                        await asyncio.sleep(1.5)
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
                    except Exception as retry_err:
                        logger.error(f"OpenAI retry also failed: {retry_err}")
                elif settings.USE_LOCAL_LLM:
                    # Chỉ fallback Qwen port nếu đang bật local LLM
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

                if not res_data:
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

                    if f_name == "tim_anh_san_pham":
                        user_lower = normalized_user_message.lower()
                        is_asking_availability = any(k in user_lower for k in [
                            "còn ko", "còn không", "con ko", "con khong", "còn hàng", "con hang",
                            "còn màu", "con mau", "còn size", "con size", "còn áo", "con ao", "còn quần", "con quan"
                        ])
                        is_explicit_view_request = any(k in user_lower for k in [
                            "cho xem", "xem ảnh", "xem anh", "gửi ảnh", "gui anh", "gửi mẫu", "gui mau",
                            "xem mẫu", "xem mau", "cho coi", "hình ảnh", "hinh anh", "ảnh áo", "anh ao", "ảnh quần", "anh quan"
                        ])
                        if is_asking_availability and not is_explicit_view_request:
                            tool_calls_made.append(f_name)
                            tool_result = {
                                "status": "in_stock",
                                "message": "Mẫu này và tất cả các màu/size bên shop LUÔN LUÔN CÒN HÀNG SẴN 100%. Trả lời cực kỳ ngắn gọn: Báo khách DẠ CÒN HÀNG và xin chiều cao cân nặng để tư vấn size. TUYỆT ĐỐI CẤM BỊA CÂU GỬI ẢNH, KHÔNG GỬI ẢNH!"
                            }
                            full_messages.append({
                                "role": "tool",
                                "tool_call_id": tc.get("id", f"call_{turn}_{f_name}"),
                                "name": f_name,
                                "content": json.dumps(tool_result, ensure_ascii=False)
                            })
                            continue

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
    # Xóa các dòng mồ côi chỉ chứa dấu gạch đầu dòng, dấu chấm tròn (do strip ảnh để lại, ví dụ: '-' hoặc '*' hoặc '•')
    reply_text = re.sub(r'(?m)^[ \t]*[-*•–—:][ \t]*$', '', reply_text)
    # Xóa dòng chỉ chứa khoảng trắng (space/tab) thành dòng trống thật
    reply_text = re.sub(r'(?m)^[ \t]+$', '', reply_text)
    # Gộp 2+ dòng trống liên tiếp thành 1 dòng trống duy nhất
    reply_text = re.sub(r'\n{2,}', '\n\n', reply_text).strip()

    # Tự động rút gọn câu giới thiệu mẫu dài dòng nếu LLM vô tình lặp lại
    reply_text = re.sub(
        r'(?i)Dạ em gửi (?:anh|chị|bạn) xem các mẫu áo (?:CBUM và Wolves|CBUM|Wolves)\s*ạ!\s*(?:Anh|Chị|Bạn) xem qua ảnh rồi ưng mẫu số mấy nhắn em nhé!\s*Đồng thời (?:anh|chị|bạn) cho em xin chiều cao và cân nặng để em tư vấn size chuẩn cho mình luôn nha!\s*[👕💪]*',
        'Dạ em gửi anh xem mẫu ạ! Anh cho em xin chiều cao và cân nặng để em chọn size chuẩn cho mình nhé! 💪',
        reply_text
    )
    reply_text = re.sub(
        r'(?i)các mẫu áo (?:CBUM và Wolves|CBUM|Wolves)\s*ạ!?',
        'mẫu ạ!',
        reply_text
    )

    # Bổ sung ảnh từ keyword trong câu chat (CHỈ KHI khách hỏi xem ảnh / xem mẫu)
    lower_user = user_message.lower()

    # KIỂM TRA 1: Khách CHỈ HỎI CÒN HÀNG HAY KHÔNG (ví dụ: 'mẫu áo basketball màu đen còn ko shop', 'màu đen còn không', 'còn size L không')
    # TUYỆT ĐỐI KHÔNG gửi bất kỳ hình ảnh nào!
    is_asking_availability = any(k in lower_user for k in [
        "còn ko", "còn không", "con ko", "con khong", "còn hàng", "con hang",
        "còn màu", "con mau", "còn size", "con size", "còn áo", "con ao", "còn quần", "con quan"
    ])
    is_explicit_view_request = any(k in lower_user for k in [
        "cho xem", "xem ảnh", "xem anh", "gửi ảnh", "gui anh", "gửi mẫu", "gui mau",
        "xem mẫu", "xem mau", "cho coi", "hình ảnh", "hinh anh", "bảng size", "bang size"
    ])

    # KIỂM TRA 2: Nếu khách đang ĐẶT HÀNG có số / mã cụ thể (ví dụ: 'lấy áo 45 46 quần 13', 'áo 30 31 quần 124')
    # TUYỆT ĐỐI KHÔNG gửi ảnh fallback!
    has_order_verb = any(w in lower_user for w in ["lấy", "lay", "đặt", "dat", "mua", "chốt", "chot"])
    has_digits = bool(re.search(r'\d+', user_message))
    is_ordering_with_codes = has_order_verb and has_digits

    # 1. Khách hỏi xem THÊM MẪU / CÒN MẪU NÀO NỮA / MẪU KHÁC / MẪU CŨ / BỘ SƯU TẬP TRƯỚC
    # -> CHỈ LÚC NÀY MỚI GỬI NHỮNG ẢNH CÒN LẠI!
    is_more_models_query = any(k in lower_user for k in [
        "còn mẫu nào nữa", "con mau nao nua", "còn mẫu nào ko", "con mau nao ko", "còn mẫu ko", "con mau ko",
        "thêm mẫu", "them mau", "xem thêm mẫu", "xem them mau", "muốn xem thêm mẫu", "muon xem them mau",
        "gửi thêm mẫu", "gui them mau", "cho thêm mẫu", "cho them mau", "còn mẫu nào", "con mau nao",
        "mẫu khác", "mau khac", "mẫu nào khác", "mau nao khac", "mẫu khác đâu", "xem mẫu khác",
        "mẫu cũ", "mau cu", "mẫu trước", "mau truoc", "bộ sưu tập cũ", "bo suu tap cu"
    ])

    if is_asking_availability and not is_explicit_view_request:
        suggested_images = []
    elif is_more_models_query:
        # Khách hỏi thêm mẫu -> Gửi các ảnh còn lại (album áo và mẫu cũ)
        for img in ALL_ANH_AO:
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
    elif is_ordering_with_codes or ("tim_anh_san_pham" in tool_calls_made and suggested_images):
        # Nếu khách mới chat hỏi mẫu chung chung, giới hạn đúng 2 ảnh mẫu mới
        is_general_model_query = any(k in lower_user for k in [
            "cho xem mẫu", "xem mẫu", "mẫu đâu", "cho xem mau", "xem mau", "sản phẩm", "san pham",
            "xem ảnh áo", "ảnh áo", "xem mẫu áo", "cac mau ao", "các mẫu áo", "cho xem áo", "xem ao",
            "gửi áo", "gửi mẫu áo", "mẫu áo", "mau ao", "có mẫu nào", "co mau nao", "shop có mẫu", "gửi mẫu", "gui mau", "mẫu mới", "mau moi"
        ])
        if is_general_model_query and not is_more_models_query:
            suggested_images = suggested_images[:2]
    else:
        # Nếu hỏi xem tất cả (cả áo lẫn quần)
        if any(k in lower_user for k in ["tất cả", "tat ca", "hết", "het", "xem hết", "all", "tất cả mẫu", "toàn bộ", "xem tất cả"]):
            for img in ["/static/products/mau_moi_1.png", "/static/products/mau_moi_2.png"] + list(ALL_ANH_AO) + list(ALL_ANH_QUAN):
                if img not in suggested_images:
                    suggested_images.append(img)

        # Nếu hỏi xem ảnh quần
        elif any(k in lower_user for k in ["xem ảnh quần", "ảnh quần", "xem mẫu quần", "cac mau quan", "các mẫu quần", "cho xem quần", "xem quan", "gửi mẫu quần", "mẫu quần"]):
            for q_img in ALL_ANH_QUAN:
                if q_img not in suggested_images:
                    suggested_images.append(q_img)

        # Khách mới chat hỏi mẫu hoặc hỏi xem mẫu áo -> Ưu tiên ảnh mẫu của Ads nếu có, hoặc gửi đúng 2 ảnh mã mới
        elif any(k in lower_user for k in [
            "mẫu mới", "mau moi", "mẫu áo mới", "mau ao moi", "áo mới", "ao moi", "mới nhất", "moi nhat",
            "cho xem mẫu", "xem mẫu", "mẫu đâu", "cho xem mau", "xem mau", "sản phẩm", "san pham",
            "xem ảnh áo", "ảnh áo", "xem mẫu áo", "cac mau ao", "các mẫu áo", "cho xem áo", "xem ao",
            "gửi áo", "gửi mẫu áo", "mẫu áo", "mau ao", "có mẫu nào", "co mau nao", "shop có mẫu", "gửi mẫu", "gui mau"
        ]) or (bool(re.search(r'\b(mới|moi|new)\b', lower_user)) and not bool(re.search(r'\bnew_\d+\b', lower_user))):
            ad_models = customer_profile.get("ad_models") if customer_profile else None
            if ad_models:
                try:
                    from app.tools.business_rules import tim_anh_san_pham
                    for c in ad_models:
                        res = tim_anh_san_pham(str(c))
                        for img in res.get("image_urls", []):
                            if img and img not in suggested_images:
                                suggested_images.append(img)
                        if len(suggested_images) >= 2:
                            break
                except Exception:
                    pass

            if not suggested_images:
                try:
                    from app.services.new_models_service import get_new_models
                    new_m = get_new_models()
                    for m in new_m[:2]:
                        img = m.get("image_url")
                        if img and img not in suggested_images:
                            suggested_images.append(img)
                except Exception:
                    pass
            if not suggested_images:
                suggested_images = ["/static/products/mau_moi_1.png", "/static/products/mau_moi_2.png"]
            suggested_images = suggested_images[:2]

        # Chỉ gửi bảng size KHI khách hỏi bảng size (tránh spam ảnh size)
        elif any(k in lower_user for k in ["bảng size", "bang size", "size chart", "bảng số đo", "bang so do", "form size"]):
            if "/static/products/bang_size.jpg" not in suggested_images:
                suggested_images.append("/static/products/bang_size.jpg")

    # BẢO VỆ 2 LỚP: Nếu đã biết số đo / size mà bot lỡ hỏi lại chiều cao cân nặng
    if (known_weight or known_size) and reply_text:
        ask_hw_pattern = re.compile(
            r'(?i)\s*(?:anh|chị|bạn)?\s*(?:cho em xin|xin|nhắn em|báo em)\s*(?:chiều cao|cân nặng|chiều cao và cân nặng|chiều cao cân nặng|số đo)[^!.\n]*[!.]?(\s*💪)?'
        )
        if ask_hw_pattern.search(reply_text):
            reply_text = ask_hw_pattern.sub('', reply_text).strip()
            # Bổ sung câu hỏi tương tác phù hợp
            has_order_verb = any(w in lower_user for w in ["lấy", "lay", "đặt", "dat", "mua", "chốt", "chot"])
            has_digits = bool(re.search(r'\d+', user_message))
            if has_order_verb and has_digits:
                reply_text += "\nAnh cho em xin địa chỉ và số điện thoại để em lên đơn gửi ship COD tận nhà cho mình nhé! 📦"
            else:
                sz_txt = f"size {known_size} " if known_size else ""
                reply_text += f"\nAnh xem qua ưng mẫu nào nhắn em để em giữ {sz_txt}cho mình nhé! 💪"

    # BẢO VỆ 3 LỚP: Đảm bảo câu trả lời luôn kết thúc bằng một câu hỏi tương tác (Call to Action)
    # Tránh trường hợp bot trả lời câu hỏi cụt ngủn rồi im lặng
    if reply_text and not any(q in reply_text for q in ["?", "không", "nha", "nhé", "nào", "chưa", "nhỉ", "📦", "💪"]):
        has_order_verb = any(w in lower_user for w in ["lấy", "lay", "đặt", "dat", "mua", "chốt", "chot"])
        has_digits = bool(re.search(r'\d+', user_message))
        if not (known_weight or known_size):
            reply_text += "\nAnh cho em xin chiều cao và cân nặng để em chọn size chuẩn cho mình nhé! 💪"
        elif not (has_order_verb and has_digits):
            sz_txt = f"size {known_size} " if known_size else ""
            reply_text += f"\nAnh xem qua ưng mẫu nào nhắn em để em giữ {sz_txt}cho mình nha! 💪"
        else:
            reply_text += "\nAnh cho em xin địa chỉ và số điện thoại để em lên đơn gửi ship cho mình nha! 📦"

    suggested_image = suggested_images[0] if suggested_images else None

    return {
        "reply_text": reply_text,
        "tool_calls_made": tool_calls_made,
        "suggested_image": suggested_image,
        "suggested_images": suggested_images,
        "updated_messages": full_messages
    }
