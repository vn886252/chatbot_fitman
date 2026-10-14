import time
import asyncio
import logging
from collections import defaultdict, OrderedDict
from fastapi import APIRouter, Request, Response
from app.config import settings
from app.services.llm_service import generate_response
from app.services.facebook_service import send_text_message, send_image_message, get_customer_name
from app.services.handover_service import (
    is_bot_sent,
    record_human_message,
    is_bot_paused,
    pause_bot,
    check_human_request_intent,
    record_last_customer
)
from app.services.telegram_service import send_handover_alert

logger = logging.getLogger(__name__)
router = APIRouter()

# Lưu lịch sử hội thoại theo từng user (sender_id)
# Tối đa 20 messages để tránh context quá dài
_conversation_history: dict[str, list] = defaultdict(list)
MAX_HISTORY = 20

# 1. Chống Facebook Webhook retry lặp lại cùng một message ID (mid)
_processed_mids: OrderedDict[str, float] = OrderedDict()
MAX_PROCESSED_MIDS = 5000
MID_TTL_SECONDS = 600.0  # 10 phút

# 2. Khóa tuần tự theo từng khách hàng (tránh race condition khi khách nhắn nhiều câu dồn dập < 1s)
_user_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# 3. Rate limiter cho tin nhắn báo lỗi/hệ thống bận (tối đa 1 thông báo mỗi 60 giây cho mỗi khách)
_last_error_sent: dict[str, float] = {}
ERROR_SUPPRESS_WINDOW = 60.0


def is_mid_duplicate(mid: str) -> bool:
    """Kiểm tra và ghi nhận mid. Trả về True nếu mid đã từng được xử lý trong cache."""
    if not mid:
        return False
    now = time.time()
    # Dọn dẹp cache quá hạn
    while _processed_mids and (now - next(iter(_processed_mids.values()))) > MID_TTL_SECONDS:
        _processed_mids.popitem(last=False)

    if mid in _processed_mids:
        return True

    _processed_mids[mid] = now
    if len(_processed_mids) > MAX_PROCESSED_MIDS:
        _processed_mids.popitem(last=False)
    return False


def should_suppress_error(sender_id: str) -> bool:
    """Trả về True nếu vừa gửi thông báo bận/lỗi cho khách này trong vòng 60 giây."""
    now = time.time()
    last_time = _last_error_sent.get(sender_id, 0.0)
    if (now - last_time) < ERROR_SUPPRESS_WINDOW:
        return True
    _last_error_sent[sender_id] = now
    return False


def _trim_history(history: list) -> list:
    """Giữ lại tối đa MAX_HISTORY messages gần nhất."""
    if len(history) > MAX_HISTORY:
        return history[-MAX_HISTORY:]
    return history


@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Xác thực Facebook Messenger Webhook
    Facebook gửi: GET /webhook?hub.mode=subscribe&hub.challenge=...&hub.verify_token=...
    """
    params = request.query_params
    hub_mode = params.get("hub.mode")
    hub_verify_token = params.get("hub.verify_token")
    hub_challenge = params.get("hub.challenge")

    logger.info(f"Received webhook verification: mode={hub_mode}, token={hub_verify_token}, challenge={hub_challenge}")

    if hub_mode == "subscribe" and hub_verify_token == settings.FB_VERIFY_TOKEN:
        logger.info("Webhook verification successful!")
        return Response(content=str(hub_challenge or ""), media_type="text/plain", status_code=200)

    logger.warning(f"Webhook verification failed! Expected token: {settings.FB_VERIFY_TOKEN}, got: {hub_verify_token}")
    return Response(content="Verification failed: token mismatch", media_type="text/plain", status_code=403)


@router.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"status": "INVALID_JSON"}

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event.get("sender", {}).get("id")
                message = event.get("message", {})

                # -------------------------------------------------------------
                # 1. Xử lý tin nhắn Echo (từ Page gửi đi)
                # -------------------------------------------------------------
                if message.get("is_echo"):
                    mid = message.get("mid")
                    app_id = message.get("app_id")

                    # Nếu là tin nhắn do chính Bot gửi qua Graph API -> bỏ qua
                    # (Facebook gửi kèm app_id nếu do Bot gửi, còn người thật gửi từ Inbox thì app_id là None/trống)
                    if is_bot_sent(mid) or (app_id is not None and str(app_id) != ""):
                        continue

                    # Nếu KHÔNG phải Bot gửi -> Chắc chắn là NGƯỜI THẬT (Admin/Nhân viên) nhắn qua Page Inbox!
                    customer_id = event.get("recipient", {}).get("id")
                    human_text = message.get("text") or "[Hình ảnh/Tệp đính kèm]"
                    if customer_id:
                        record_last_customer(customer_id)
                        is_first = record_human_message(customer_id)
                        if is_first:
                            customer_name = await get_customer_name(customer_id)
                            await send_handover_alert(
                                customer_id=customer_id,
                                customer_name=customer_name,
                                event_type="human_chatting",
                                user_text=human_text
                            )
                    continue

                # -------------------------------------------------------------
                # 1b. Ghi nhận khi Admin đọc tin nhắn của khách
                # -------------------------------------------------------------
                if "read" in event:
                    recipient_id = event.get("recipient", {}).get("id")
                    if recipient_id:
                        record_last_customer(recipient_id)

                # -------------------------------------------------------------
                # 2. Xử lý tin nhắn từ Khách hàng
                # -------------------------------------------------------------
                user_text = message.get("text")
                mid = message.get("mid")
                attachments = message.get("attachments") or []
                is_sticker = bool(message.get("sticker_id"))

                # Chống Facebook Webhook retry xử lý lặp lại cùng một mid
                if mid and is_mid_duplicate(mid):
                    logger.info(f"[Webhook] Duplicate mid '{mid}' from sender {sender_id}. Skipping retry.")
                    continue

                image_urls = []
                if not is_sticker and attachments:
                    for att in attachments:
                        if att.get("type") == "image":
                            p_url = att.get("payload", {}).get("url")
                            if p_url:
                                image_urls.append(p_url)

                has_image = len(image_urls) > 0

                if sender_id and (user_text or has_image):
                    record_last_customer(sender_id)
                    user_lock = _user_locks[sender_id]
                    async with user_lock:
                        try:
                            # Kiểm tra xem Bot có đang bị tạm dừng với khách này không (do người thật đang chat hoặc mới yêu cầu)
                            paused, remaining = is_bot_paused(sender_id)
                            if paused:
                                logger.info(f"[Handover] Bot is paused for customer {sender_id} ({remaining:.0f}s left). Skipping auto-reply.")
                                continue

                            # 2a. Nếu khách hàng gửi HÌNH ẢNH (mẫu áo/quần)
                            if has_image:
                                logger.info(f"[Image] Customer {sender_id} sent image(s): {len(image_urls)}")
                                customer_name = await get_customer_name(sender_id)

                                # Gửi cảnh báo ngay cho shop owner qua Telegram (kèm ảnh nếu có)
                                await send_handover_alert(
                                    customer_id=sender_id,
                                    customer_name=customer_name,
                                    event_type="customer_sent_image",
                                    user_text=user_text or "[Đã gửi ảnh mẫu]",
                                    image_url=image_urls[0] if image_urls else None
                                )

                                # Phản hồi nhẹ nhàng giữ chân khách trên Facebook Messenger
                                if user_text:
                                    image_reply = (
                                        "Dạ shop đã nhận được ảnh mẫu của anh/chị rồi ạ! "
                                        "Em đã báo nhân viên vào kiểm tra mẫu ngay cho mình trong ít phút nhé ạ! 💪\n\n"
                                        "Anh/chị có thể nhắn thêm chiều cao + cân nặng để shop hỗ trợ tư vấn size luôn nha!"
                                    )
                                else:
                                    image_reply = (
                                        "Dạ shop đã nhận được ảnh mẫu của anh/chị rồi ạ! "
                                        "Anh/chị đợi nhân viên shop kiểm tra kho và phản hồi lại ngay trong ít phút nhé ạ! 💪\n\n"
                                        "(Hoặc anh/chị có thể nhắn trước chiều cao + cân nặng để shop chọn size luôn nha)"
                                    )

                                await send_text_message(sender_id, image_reply)
                                history_entry = f"[Khách gửi ảnh mẫu]{f': {user_text}' if user_text else ''}"
                                _conversation_history[sender_id].append({"role": "user", "content": history_entry})
                                _conversation_history[sender_id].append({"role": "assistant", "content": image_reply})
                                continue

                            # Kiểm tra nếu khách hàng yêu cầu gặp người thật / nhân viên
                            if check_human_request_intent(user_text):
                                logger.info(f"[Handover] Customer {sender_id} requested human: '{user_text}'")
                                pause_bot(sender_id, reason="customer_requested")
                                customer_name = await get_customer_name(sender_id)

                                # Gửi cảnh báo ngay cho shop owner qua Telegram
                                await send_handover_alert(
                                    customer_id=sender_id,
                                    customer_name=customer_name,
                                    event_type="customer_requested",
                                    user_text=user_text
                                )

                                # Phản hồi nhẹ nhàng cho khách rồi dừng tự động
                                handoff_reply = "Dạ em đã thông báo cho nhân viên shop rồi ạ! Anh/chị đợi nhân viên vào hỗ trợ mình trong giây lát nha! 💪"
                                await send_text_message(sender_id, handoff_reply)
                                _conversation_history[sender_id].append({"role": "user", "content": user_text})
                                _conversation_history[sender_id].append({"role": "assistant", "content": handoff_reply})
                                continue

                            # Lấy lịch sử hội thoại của user này
                            history = _trim_history(_conversation_history[sender_id])

                            # Lấy tên khách hàng từ Facebook Graph API
                            customer_name = await get_customer_name(sender_id)

                            res = await generate_response(
                                history,
                                user_text,
                                customer_name=customer_name,
                                sender_id=sender_id
                            )
                            reply_text = res.get("reply_text", "")
                            suggested_images = res.get("suggested_images") or []
                            if not suggested_images and res.get("suggested_image"):
                                suggested_images = [res.get("suggested_image")]

                            # Cập nhật lịch sử — chỉ lưu user + assistant có text content
                            # Bỏ: role=system, role=tool, assistant chỉ có tool_calls (không có text)
                            updated = res.get("updated_messages", [])
                            if updated:
                                clean_history = []
                                for m in updated:
                                    role = m.get("role")
                                    if role == "user":
                                        clean_history.append(m)
                                    elif role == "assistant" and m.get("content"):
                                        # Chỉ lưu assistant message có nội dung text thực sự
                                        clean_history.append({"role": "assistant", "content": m["content"]})
                                # Gán history sau khi đã duyệt hết toàn bộ updated messages
                                _conversation_history[sender_id] = clean_history

                            # Gửi câu trả lời văn bản
                            if reply_text:
                                # Nếu là câu thông báo bận/lỗi hệ thống, áp dụng rate-limit để không spam khách
                                if "Hiện tại hệ thống đang bận" in reply_text:
                                    if not should_suppress_error(sender_id):
                                        await send_text_message(sender_id, reply_text)
                                    else:
                                        logger.warning(f"[Webhook] Suppressed repeated busy error message for {sender_id}.")
                                else:
                                    await send_text_message(sender_id, reply_text)

                            # Gửi tất cả ảnh đính kèm
                            for img in suggested_images:
                                await send_image_message(sender_id, img)

                        except Exception as e:
                            logger.error(f"Error handling message for {sender_id}: {e}", exc_info=True)
                            if not should_suppress_error(sender_id):
                                await send_text_message(
                                    sender_id,
                                    "Dạ em chào anh! Hiện tại hệ thống đang bận một chút, anh vui lòng nhắn lại sau ít phút nhé ạ."
                                )
                            else:
                                logger.warning(f"[Webhook] Suppressed repeated exception error message for {sender_id}.")

        return {"status": "EVENT_RECEIVED"}
    return {"status": "NOT_A_PAGE_EVENT"}
