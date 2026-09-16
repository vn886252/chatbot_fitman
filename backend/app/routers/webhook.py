import logging
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from app.config import settings
from app.services.llm_service import generate_response
from app.services.facebook_service import send_text_message, send_image_message

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == settings.FB_VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge or "", status_code=200)
    raise HTTPException(status_code=403, detail="Verification failed: token mismatch")

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
                        res = await generate_response([], user_text)
                        reply_text = res.get("reply_text")
                        suggested_images = res.get("suggested_images") or []
                        if not suggested_images and res.get("suggested_image"):
                            suggested_images = [res.get("suggested_image")]

                        # Gửi câu trả lời văn bản
                        if reply_text:
                            await send_text_message(sender_id, reply_text)
                        
                        # Gửi tất cả ảnh đính kèm
                        for img in suggested_images:
                            await send_image_message(sender_id, img)

                    except Exception as e:
                        logger.error(f"Error handling message for {sender_id}: {e}")
                        await send_text_message(sender_id, "Dạ em chào anh! Hiện tại hệ thống đang bận một chút, anh vui lòng nhắn lại sau ít phút nhé ạ.")

        return {"status": "EVENT_RECEIVED"}
    return {"status": "NOT_A_PAGE_EVENT"}
