import os
import json
import logging
import httpx
from app.config import settings, ROOT_DIR
from app.services.handover_service import record_bot_sent, record_bot_outgoing

logger = logging.getLogger(__name__)

# URL gốc của ảnh — ưu tiên SERVER_BASE_URL từ env (Render),
# fallback về fitman.vn nếu không cấu hình
def _get_base_url() -> str:
    if settings.SERVER_BASE_URL and "your-app-name" not in settings.SERVER_BASE_URL:
        return settings.SERVER_BASE_URL.rstrip("/")
    return "https://chatbot-fitman.onrender.com"


def _resolve_image_url(image_path: str) -> str:
    """Chuyển đường dẫn /static/... thành URL đầy đủ để Facebook tải được."""
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path
    base = _get_base_url()
    return f"{base}{image_path}"


async def get_customer_name(recipient_id: str) -> str:
    """Lấy tên thật của khách hàng từ Facebook Graph API."""
    if not settings.FB_PAGE_ACCESS_TOKEN or not recipient_id:
        return "Khách hàng"
    url = f"https://graph.facebook.com/v19.0/{recipient_id}?fields=first_name,last_name,name&access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                return data.get("name") or "Khách hàng"
    except Exception as e:
        logger.warning(f"Could not fetch Facebook profile for {recipient_id}: {e}")
    return "Khách hàng"


async def send_text_message(recipient_id: str, text: str, notification_type: str = "REGULAR") -> bool:
    record_bot_outgoing(recipient_id, text)
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "notification_type": notification_type,
        "message": {"text": text}
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                try:
                    res_json = response.json()
                    mid = res_json.get("message_id")
                    if mid:
                        record_bot_sent(mid)
                except Exception:
                    pass
                return True
            else:
                logger.error(f"Failed to send text message: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Exception occurred while sending text message: {e}")
        return False


async def send_image_message(recipient_id: str, image_url: str, notification_type: str = "REGULAR") -> bool:
    """
    Gửi ảnh cho khách qua Facebook Messenger Send API.
    1. Ưu tiên: Nếu ảnh có file cục bộ trên máy chủ (ví dụ /static/products/...),
       upload trực tiếp bằng multipart/form-data (filedata).
       -> Hoạt động 100% tin cậy trên cả Localhost, Render, Ngrok mà không phụ thuộc vào domain ngoài!
    2. Fallback: Nếu không tìm thấy file cục bộ hoặc là URL http/https, gửi qua URL payload.
    """
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    record_bot_outgoing(recipient_id, image_url)

    # 1. Xác định đường dẫn file cục bộ trên server
    local_path = None
    if image_url.startswith("/") or not (image_url.startswith("http://") or image_url.startswith("https://")):
        clean_rel = image_url.lstrip("/")
        candidate = os.path.join(ROOT_DIR, clean_rel)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            local_path = candidate
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidate2 = os.path.join(base_dir, clean_rel)
            if os.path.exists(candidate2) and os.path.isfile(candidate2):
                local_path = candidate2
    elif os.path.isabs(image_url) and os.path.exists(image_url) and os.path.isfile(image_url):
        local_path = image_url

    # 2. Upload trực tiếp filedata nếu file tồn tại trên ổ đĩa
    if local_path and os.path.exists(local_path) and os.path.isfile(local_path):
        logger.info(f"Directly uploading local image to Facebook: {local_path}")
        try:
            filename = os.path.basename(local_path)
            content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
            with open(local_path, "rb") as f:
                file_bytes = f.read()

            data = {
                "recipient": json.dumps({"id": recipient_id}),
                "messaging_type": "RESPONSE",
                "notification_type": notification_type,
                "message": json.dumps({
                    "attachment": {
                        "type": "image",
                        "payload": {"is_reusable": True}
                    }
                })
            }
            files = {
                "filedata": (filename, file_bytes, content_type)
            }
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(url, data=data, files=files)
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                        mid = res_json.get("message_id")
                        if mid:
                            record_bot_sent(mid)
                    except Exception:
                        pass
                    logger.info(f"Local image uploaded successfully to {recipient_id}.")
                    return True
                else:
                    logger.warning(f"Direct file upload to Facebook returned {response.status_code}: {response.text}. Falling back to URL payload.")
        except Exception as e:
            logger.warning(f"Error during local file upload to Facebook: {e}. Falling back to URL payload.")

    # 3. Fallback: Gửi qua URL payload
    full_url = _resolve_image_url(image_url)
    logger.info(f"Sending image via URL payload: {full_url}")

    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "notification_type": notification_type,
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
                try:
                    res_json = response.json()
                    mid = res_json.get("message_id")
                    if mid:
                        record_bot_sent(mid)
                except Exception:
                    pass
                return True
            else:
                logger.error(f"Failed to send image message: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Exception occurred while sending image message: {e}")
        return False


async def send_image_grid(recipient_id: str, images: list[str]) -> bool:
    """
    Gửi cụm ảnh dạng Image Grid / Attachments Album của Facebook Messenger (2 đến 6 ảnh).
    Facebook tự động xếp các ảnh thành cụm lưới / album trong 1 tin nhắn duy nhất:
    - Chỉ phát đúng 1 tiếng chuông (ting) duy nhất.
    - Khách chạm vào ảnh nào là mở to toàn màn hình ảnh đó để phóng to/zoom rõ nét.
    - Không bị cắt xén, không có card chữ vướng víu như Carousel.
    """
    if not settings.FB_PAGE_ACCESS_TOKEN or not recipient_id or not images:
        return False

    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    for u in images[:6]:
        record_bot_outgoing(recipient_id, u)
    resolved_urls = [_resolve_image_url(img) for img in images[:6]]
    if len(resolved_urls) < 2:
        return False

    # 1. Thử gửi dạng Image Grid Template
    grid_images = [{"url": u} for u in resolved_urls]
    payload_grid = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "image_grid",
                    "elements": [
                        {
                            "images": grid_images
                        }
                    ]
                }
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload_grid)
            if response.status_code == 200:
                try:
                    res_json = response.json()
                    mid = res_json.get("message_id")
                    if mid:
                        record_bot_sent(mid)
                except Exception:
                    pass
                logger.info(f"Image grid ({len(grid_images)} images) sent successfully to {recipient_id}.")
                return True
            else:
                logger.warning(f"Facebook image_grid returned {response.status_code}: {response.text}. Trying attachments array fallback.")
    except Exception as e:
        logger.warning(f"Exception sending image_grid: {e}")

    # 2. Thử gửi dạng attachments array (Official Messenger Multi-image Album)
    payload_attachments = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {
            "attachments": [
                {
                    "type": "image",
                    "payload": {
                        "url": u,
                        "is_reusable": True
                    }
                }
                for u in resolved_urls
            ]
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload_attachments)
            if response.status_code == 200:
                try:
                    res_json = response.json()
                    mid = res_json.get("message_id")
                    if mid:
                        record_bot_sent(mid)
                except Exception:
                    pass
                logger.info(f"Attachments album ({len(resolved_urls)} images) sent successfully to {recipient_id}.")
                return True
            else:
                logger.warning(f"Facebook attachments array returned {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.warning(f"Exception sending attachments array: {e}")
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


async def send_image_carousel(recipient_id: str, images: list[str]) -> bool:
    """
    Gửi cụm ảnh dạng Generic Template (Carousel) của Facebook Messenger.
    Giúp gộp các ảnh vào 1 tin nhắn duy nhất trượt ngang, không spam nhiều thông báo cho khách.
    """
    if not settings.FB_PAGE_ACCESS_TOKEN or not recipient_id or not images:
        return False

    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={settings.FB_PAGE_ACCESS_TOKEN}"
    elements = []
    for idx, img in enumerate(images[:10], 1):
        full_url = _resolve_image_url(img)
        title = f"Mẫu {idx}"
        subtitle = "Cotton 100% 260GSM, Form Oversize Gym Bro"
        img_low = img.lower()
        if "mau_moi_1" in img_low or "moi1" in img_low:
            title = "Mẫu mới 1: Trắng / Kem"
            subtitle = "Form Oversize CBUM, Cotton 260GSM"
        elif "mau_moi_2" in img_low or "moi2" in img_low:
            title = "Mẫu mới 2: Đen"
            subtitle = "Form Oversize CBUM, Cotton 260GSM"
        elif "model_b1" in img_low:
            title = "Mẫu B1: Basketball Trắng"
        elif "model_b2" in img_low:
            title = "Mẫu B2: Basketball Đen"
        elif "nhom_1" in img_low:
            title = "Áo CBUM Đen (Mẫu 1-20)"
        elif "nhom_2" in img_low:
            title = "Áo CBUM Trắng (Mẫu 2-14)"
        elif "nhom_3" in img_low:
            title = "Quần short CBUM (Q1-Q4)"
        elif "nhom_4" in img_low:
            title = "Áo Wolves / Punk"
        elif "nhom_5" in img_low:
            title = "Áo CBUM & Quần (Q6-Q7)"
        elif "nhom_6" in img_low:
            title = "Áo CBUM (Mẫu 43-47)"

        elements.append({
            "title": title,
            "image_url": full_url,
            "subtitle": subtitle
        })

    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements
                }
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                try:
                    res_json = response.json()
                    mid = res_json.get("message_id")
                    if mid:
                        record_bot_sent(mid)
                except Exception:
                    pass
                logger.info(f"Image carousel ({len(elements)} items) sent successfully to {recipient_id}.")
                return True
            else:
                logger.warning(f"Facebook carousel returned {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.warning(f"Exception sending image carousel: {e}")
        return False

