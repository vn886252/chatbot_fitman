import httpx
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_text_message(recipient_id: str, text: str) -> bool:
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text}
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Failed to send text message: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Exception occurred while sending text message: {e}")
        return False

async def send_image_message(recipient_id: str, image_url: str) -> bool:
    if image_url.startswith("/static/") and settings.SERVER_BASE_URL:
        full_url = f"{settings.SERVER_BASE_URL.rstrip('/')}{image_url}"
    else:
        full_url = image_url

    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": full_url,
                    "is_reusable": True
                }
            }
        }
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Failed to send image message: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Exception occurred while sending image message: {e}")
        return False

async def send_quick_replies(recipient_id: str, text: str, options: list[dict]) -> bool:
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {
            "text": text,
            "quick_replies": options
        }
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Failed to send quick replies: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Exception occurred while sending quick replies: {e}")
        return False
