import json
import os
import re
import logging
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
import httpx
from app.config import settings, ROOT_DIR

logger = logging.getLogger(__name__)

# File data: backend/app/data/new_models.json
def _get_data_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "new_models.json"))

def _load_models() -> Dict[str, Any]:
    data_path = _get_data_path()
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("Failed to load models data, returning default.")
        return {"max_display": 6, "models": []}

def _save_models(data: Dict[str, Any]) -> None:
    data_path = _get_data_path()
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def parse_model_caption(caption: str) -> Tuple[Optional[str], str]:
    """
    Phân tích caption chủ shop gửi khi upload ảnh để lấy mã mẫu và mô tả.
    Ví dụ:
    - '48' -> ('48', 'Mẫu 48')
    - '48 Áo CBUM đen' -> ('48', 'Áo CBUM đen')
    - 'mã 49: áo thun' -> ('49', 'áo thun')
    - 'W8 Áo Wolves punk' -> ('W8', 'Áo Wolves punk')
    - 'Q8 Quần đùi tập gym' -> ('Q8', 'Quần đùi tập gym')
    - '' hoặc 'thêm mẫu' -> (None, '')
    """
    if not caption:
        return (None, "")

    text = caption.strip()
    # Loại bỏ các tiền tố như "mã:", "mã", "mẫu:", "mẫu", "#" ở đầu
    cleaned = re.sub(r'^(mã|mẫu|ma|mau)\s*[:\-]?\s*', '', text, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'^#\s*', '', cleaned).strip()

    # Nếu sau khi loại bỏ tiền tố chỉ còn các từ chung chung
    if not cleaned or cleaned.lower() in ["mới", "moi", "ảnh", "anh", "thêm", "them", "mẫu mới", "mau moi", "thêm mẫu", "them mau"]:
        return (None, "")

    # Tách từ đầu tiên làm mã mẫu
    parts = cleaned.split(None, 1)
    raw_code = parts[0].strip(":-_.,;")
    # Không nhận các từ chung chung làm mã
    if raw_code.lower() in ["ảnh", "anh", "mới", "moi", "thêm", "them", "shop", "xem", "cho"]:
        return (None, "")

    model_id = raw_code.upper()

    # Phần còn lại là mô tả
    if len(parts) > 1 and parts[1].strip():
        desc = re.sub(r'^[:\-]\s*', '', parts[1].strip()).strip()
        description = desc if desc else f"Mẫu {model_id}"
    else:
        description = f"Mẫu {model_id}"

    return (model_id, description)

def get_new_models() -> List[Dict[str, Any]]:
    """Trả về tối đa max_display (6) mẫu MỚI NHẤT (cuối danh sách)."""
    data = _load_models()
    models = data.get("models", [])
    max_display = data.get("max_display", 6)
    return models[-max_display:] if models else []

def get_old_models() -> List[Dict[str, Any]]:
    """Trả về các mẫu đã bị đẩy ra khỏi sliding window (đầu danh sách)."""
    data = _load_models()
    models = data.get("models", [])
    max_display = data.get("max_display", 6)
    return models[:-max_display] if len(models) > max_display else []

def add_new_model(image_url: str, model_id: str, description: str = "") -> Dict[str, Any]:
    """
    Thêm model mới với mã do chủ shop tự đặt, hoặc cập nhật nếu mã đã tồn tại.
    Trả về model vừa thêm/cập nhật.
    """
    data = _load_models()
    clean_id = str(model_id).strip().upper()
    added_at = datetime.now().isoformat()
    desc = description if description else f"Mẫu {clean_id}"

    # Kiểm tra xem mã đã tồn tại chưa
    existing_idx = -1
    for i, m in enumerate(data.get("models", [])):
        if str(m.get("id", "")).strip().upper() == clean_id:
            existing_idx = i
            break

    new_model = {
        "id": clean_id,
        "image_url": image_url,
        "description": desc,
        "added_at": added_at
    }

    if existing_idx >= 0:
        # Cập nhật và đưa lên vị trí mới nhất
        data["models"].pop(existing_idx)
        data["models"].append(new_model)
    else:
        data.setdefault("models", []).append(new_model)

    _save_models(data)
    return new_model

def remove_model(model_id: str) -> bool:
    """Xóa model theo id (không phân biệt hoa thường). Trả về True nếu xóa thành công."""
    data = _load_models()
    models = data.get("models", [])
    clean_id = str(model_id).strip().upper()
    for i, model in enumerate(models):
        if str(model.get("id", "")).strip().upper() == clean_id:
            models.pop(i)
            _save_models(data)
            return True
    return False

def find_model_by_id(model_id: str) -> Optional[Dict[str, Any]]:
    """Tìm model theo mã (không phân biệt hoa thường)."""
    if not model_id:
        return None
    data = _load_models()
    clean_id = str(model_id).strip().upper()
    for m in data.get("models", []):
        if str(m.get("id", "")).strip().upper() == clean_id:
            return m
    return None

def list_all_models() -> Dict[str, Any]:
    """Trả về dict gồm new (6 mẫu mới nhất), old (mẫu cũ), total."""
    data = _load_models()
    models = data.get("models", [])
    max_display = data.get("max_display", 6)
    new_models = models[-max_display:] if models else []
    old_models = models[:-max_display] if len(models) > max_display else []
    return {
        "new": new_models,
        "old": old_models,
        "total": len(models)
    }

async def download_telegram_photo(file_id: str, model_id: Optional[str] = None) -> Optional[str]:
    """Download ảnh từ Telegram API, lưu vào static/products/new_models/ với tên theo mã mẫu."""
    token = settings.TELEGRAM_BOT_TOKEN
    async with httpx.AsyncClient() as client:
        # Lấy file_path từ Telegram
        response = await client.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}")
        result = response.json()
        if not result.get("ok"):
            logger.error(f"Telegram getFile failed: {result}")
            return None
        tg_file_path = result["result"]["file_path"]

        # Download file content
        content_resp = await client.get(f"https://api.telegram.org/file/bot{token}/{tg_file_path}")
        if content_resp.status_code != 200:
            logger.error(f"Telegram download failed: status={content_resp.status_code}")
            return None

        # Đặt tên file theo mã mẫu (loại bỏ ký tự nguy hiểm cho file)
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(model_id or "model"))
        file_name = f"model_{safe_id}.jpg"

        file_path_abs = os.path.join(ROOT_DIR, "static", "products", "new_models", file_name)
        os.makedirs(os.path.dirname(file_path_abs), exist_ok=True)
        with open(file_path_abs, "wb") as f:
            f.write(content_resp.content)

        logger.info(f"Downloaded Telegram photo to {file_path_abs}")
        return f"/static/products/new_models/{file_name}"
