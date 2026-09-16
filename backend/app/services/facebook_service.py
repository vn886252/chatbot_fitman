import httpx
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# URL gốc của ảnh — ưu tiên SERVER_BASE_URL từ env (Render),
# fallback về fitman.vn nếu không cấu hình
def _get_base_url() -> str:
    if settings.SERVER_BASE_URL and "your-app-name" not in settings.SERVER_BASE_URL:
        return settings.SERVER_BASE_URL.rstrip("/")
    return "https://fitman.vn"


def _resolve_image_url(image_path: str) -> str:
    """Chuyển đường dẫn /static/... thành URL đầy đủ để Facebook tải được."""
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path
    base = _get_base_url()
    return f"{base}{image_path}"


async def send_text_message(recipient_id: str, text: str) -> bool:
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text}
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
    full_url = _resolve_image_url(image_url)
    logger.info(f"Sending image: {full_url}")

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
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Failed to send quick replies: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Exception occurred while sending quick replies: {e}")
        return False
