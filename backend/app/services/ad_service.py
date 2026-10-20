import os
import json
import re
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

CAMPAIGNS_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "ad_campaigns.json")
)


def load_ad_campaigns() -> List[Dict[str, Any]]:
    """Đọc danh sách các chiến dịch quảng cáo cấu hình từ file JSON."""
    if not os.path.exists(CAMPAIGNS_FILE):
        return []
    try:
        with open(CAMPAIGNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading ad_campaigns.json: {e}")
        return []


def save_ad_campaigns(campaigns: List[Dict[str, Any]]) -> None:
    """Lưu danh sách chiến dịch quảng cáo vào file JSON."""
    os.makedirs(os.path.dirname(CAMPAIGNS_FILE), exist_ok=True)
    try:
        with open(CAMPAIGNS_FILE, "w", encoding="utf-8") as f:
            json.dump(campaigns, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving ad_campaigns.json: {e}")


def get_campaign_images(campaign: Dict[str, Any]) -> List[str]:
    """
    Lấy danh sách link ảnh sản phẩm tương ứng với chiến dịch quảng cáo.
    Ưu tiên: image_urls định sẵn -> tra cứu theo model_codes -> photo_url từ Facebook Ads -> mẫu mới fallback.
    """
    if not campaign:
        return ["/static/products/mau_moi_1.png", "/static/products/mau_moi_2.png"]

    # 1. Nếu chiến dịch có chỉ định sẵn image_urls
    if campaign.get("image_urls"):
        return campaign["image_urls"][:2]

    # 2. Tra cứu từ kho theo model_codes
    model_codes = campaign.get("model_codes") or []
    found_images: List[str] = []

    try:
        from app.tools.business_rules import tim_anh_san_pham
        for code in model_codes:
            res = tim_anh_san_pham(str(code))
            imgs = res.get("image_urls") or []
            if not imgs and res.get("image_url"):
                imgs = [res["image_url"]]
            for img in imgs:
                if img and img not in found_images:
                    found_images.append(img)
                if len(found_images) >= 2:
                    break
            if len(found_images) >= 2:
                break
    except Exception as e:
        logger.warning(f"Error resolving images for model_codes {model_codes}: {e}")

    if found_images:
        return found_images[:2]

    # 3. Sử dụng photo_url trực tiếp từ quảng cáo nếu có
    if campaign.get("photo_url"):
        return [campaign["photo_url"]]

    # 4. Fallback mẫu mới
    return ["/static/products/mau_moi_1.png", "/static/products/mau_moi_2.png"]


def resolve_ad_campaign(referral_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Nhận diện chiến dịch quảng cáo dựa vào dữ liệu referral từ Facebook Messenger:
    - ref: tham số payload/ref từ Ads Manager
    - ad_id: ID bài quảng cáo
    - ad_title: tiêu đề trong ads_context_data
    - photo_url: ảnh trong ads_context_data
    """
    if not referral_data or not isinstance(referral_data, dict):
        return None

    raw_ref = str(referral_data.get("ref") or "").strip()
    ad_id = str(referral_data.get("ad_id") or "").strip()
    source = str(referral_data.get("source") or "").upper()
    ads_context = referral_data.get("ads_context_data") or {}
    ad_title = str(ads_context.get("ad_title") or "").strip()
    photo_url = str(ads_context.get("photo_url") or "").strip()

    # Nếu không có bất kỳ dấu hiệu quảng cáo nào
    if not raw_ref and not ad_id and source != "ADS" and not ad_title:
        return None

    campaigns = load_ad_campaigns()
    ref_clean = raw_ref.lower().strip()
    title_clean = ad_title.lower().strip()

    matched_campaign: Optional[Dict[str, Any]] = None

    # 1. So khớp chính xác theo ref_keys
    if ref_clean:
        for c in campaigns:
            ref_keys = [k.lower() for k in c.get("ref_keys", [])]
            if ref_clean in ref_keys:
                matched_campaign = dict(c)
                break

    # 2. So khớp theo ad_id
    if not matched_campaign and ad_id:
        for c in campaigns:
            configured_ad_ids = [str(aid).strip() for aid in c.get("ad_ids", [])]
            if ad_id in configured_ad_ids:
                matched_campaign = dict(c)
                break

    # 3. So khớp theo từ khóa trong ad_title
    if not matched_campaign and title_clean:
        for c in campaigns:
            keywords = [kw.lower() for kw in c.get("title_keywords", [])]
            if any(kw in title_clean for kw in keywords):
                matched_campaign = dict(c)
                break

    # 4. Tự động nhận diện động: Nếu ref là một mã sản phẩm cụ thể (ví dụ 'mau_48', '48', 'w8', 'q1')
    if not matched_campaign and ref_clean:
        # Bỏ tiền tố mau_, ao_, quan_, model_
        pure_code = re.sub(r'^(mau_|ao_|quan_|model_)', '', ref_clean).strip().upper()
        if pure_code:
            try:
                from app.tools.business_rules import tim_anh_san_pham
                res = tim_anh_san_pham(pure_code)
                imgs = res.get("image_urls") or ([res["image_url"]] if res.get("image_url") else [])
                if imgs:
                    matched_campaign = {
                        "id": f"dynamic_{pure_code.lower()}",
                        "name": f"Sản phẩm Mẫu {pure_code}",
                        "ref_keys": [ref_clean, pure_code.lower()],
                        "model_codes": [pure_code],
                        "image_urls": imgs[:2],
                        "greeting_text": (
                            f"Dạ em chào anh! Em gửi anh xem chi tiết mẫu {pure_code} trong quảng cáo bên em nha! 💪 "
                            f"Mẫu này form chuẩn tôn dáng cực đẹp ạ.\n"
                            f"Anh cho em xin chiều cao và cân nặng để em chọn size vừa vặn nhất cho mình nhé! 💪"
                        )
                    }
            except Exception as e:
                logger.warning(f"Dynamic ad model check failed for {pure_code}: {e}")

    # 5. Nếu không khớp mẫu cụ thể nào nhưng chắc chắn là từ ADS -> Fallback chiến dịch mẫu mới
    if not matched_campaign:
        matched_campaign = {
            "id": "ad_general",
            "name": ad_title if ad_title else "Quảng cáo Fitman",
            "ref_keys": [ref_clean] if ref_clean else [],
            "model_codes": ["mau_moi"],
            "photo_url": photo_url,
            "greeting_text": (
                "Dạ em chào anh! Em gửi anh xem mẫu mới trong bài quảng cáo bên em nha! 💪 "
                "Bên em có sẵn đủ size cho mình luôn ạ.\n"
                "Anh cho em xin chiều cao và cân nặng để em chọn size chuẩn cho mình nhé! 💪"
            )
        }

    # Bổ sung các thông tin ngữ cảnh thực tế từ Facebook
    result = dict(matched_campaign)
    result["ad_id"] = ad_id
    result["ad_ref"] = raw_ref
    result["ad_title"] = ad_title
    result["photo_url"] = photo_url
    result["source"] = "facebook_ads"
    result["resolved_images"] = get_campaign_images(result)

    return result
