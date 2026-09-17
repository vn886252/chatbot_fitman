import logging
from collections import defaultdict
from fastapi import APIRouter, Request, Response
from app.config import settings
from app.services.llm_service import generate_response
from app.services.facebook_service import send_text_message, send_image_message, get_customer_name

logger = logging.getLogger(__name__)
router = APIRouter()

# Lưu lịch sử hội thoại theo từng user (sender_id)
# Tối đa 20 messages để tránh context quá dài
_conversation_history: dict[str, list] = defaultdict(list)
MAX_HISTORY = 20


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

                if message.get("is_echo"):
                    continue

                user_text = message.get("text")
                if sender_id and user_text:
                    try:
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
                            _conversation_history[sender_id] = clean_history

                        # Gửi câu trả lời văn bản
                        if reply_text:
                            await send_text_message(sender_id, reply_text)

                        # Gửi tất cả ảnh đính kèm
                        for img in suggested_images:
                            await send_image_message(sender_id, img)

                    except Exception as e:
                        logger.error(f"Error handling message for {sender_id}: {e}", exc_info=True)
                        await send_text_message(
                            sender_id,
                            "Dạ em chào anh! Hiện tại hệ thống đang bận một chút, anh vui lòng nhắn lại sau ít phút nhé ạ."
                        )

        return {"status": "EVENT_RECEIVED"}
    return {"status": "NOT_A_PAGE_EVENT"}
