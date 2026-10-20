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
    post_id = str(ads_context.get("post_id") or "").strip()
    ad_title = str(ads_context.get("ad_title") or "").strip()
    photo_url = str(ads_context.get("photo_url") or "").strip()

    # Nếu không có bất kỳ dấu hiệu quảng cáo nào
    if not raw_ref and not ad_id and not post_id and source != "ADS" and not ad_title:
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

    # 2. So khớp theo ad_id hoặc post_id (ID bài viết trên Fanpage)
    if not matched_campaign and (ad_id or post_id):
        for c in campaigns:
            configured_ad_ids = [str(aid).strip() for aid in c.get("ad_ids", [])]
            configured_post_ids = [str(pid).strip() for pid in c.get("post_ids", [])]
            # Kiểm tra ad_id
            if ad_id and ad_id in configured_ad_ids:
                matched_campaign = dict(c)
                break
            # Kiểm tra post_id (hỗ trợ cả dạng PAGEID_POSTID và số POSTID đơn)
            if post_id:
                for c_pid in configured_post_ids:
                    if c_pid == post_id or post_id.endswith(f"_{c_pid}") or c_pid.endswith(f"_{post_id}"):
                        matched_campaign = dict(c)
                        break
            if matched_campaign:
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
    result["post_id"] = post_id
    result["ad_ref"] = raw_ref
    result["ad_title"] = ad_title
    result["photo_url"] = photo_url
    result["source"] = "facebook_ads"
    result["resolved_images"] = get_campaign_images(result)

    return result


AD_SPEND_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "ad_spend.json")
)


def load_ad_spends() -> List[Dict[str, Any]]:
    """Đọc danh sách chi phí quảng cáo đã ghi nhận từ file JSON."""
    if not os.path.exists(AD_SPEND_FILE):
        return []
    try:
        with open(AD_SPEND_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading ad_spend.json: {e}")
        return []


def save_ad_spends(spends: List[Dict[str, Any]]) -> None:
    """Lưu danh sách chi phí quảng cáo vào file JSON."""
    os.makedirs(os.path.dirname(AD_SPEND_FILE), exist_ok=True)
    try:
        with open(AD_SPEND_FILE, "w", encoding="utf-8") as f:
            json.dump(spends, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving ad_spend.json: {e}")


def parse_currency_amount(text: str) -> Optional[int]:
    """Phân tích chuỗi số tiền như 200k, 200000, 200.000, 1.5tr thành số nguyên int."""
    raw = text.lower().strip()
    # Check triệu / tr / m
    m_tr = re.match(r"^(\d+(?:[\.,]\d+)?)\s*(tr|trieu|triệu|m)$", raw)
    if m_tr:
        num = float(m_tr.group(1).replace(",", "."))
        return int(num * 1_000_000)
    # Check k / nghìn
    m_k = re.match(r"^(\d+(?:[\.,]\d+)?)\s*(k|nghin|nghìn)$", raw)
    if m_k:
        num = float(m_k.group(1).replace(",", "."))
        return int(num * 1_000)
    # Check số thông thường: nếu dãy số >= 10 chữ số thì là Post ID / Ad ID, không phải số tiền
    clean_digits = re.sub(r"[^\d]", "", raw)
    if clean_digits.isdigit() and len(clean_digits) < 10:
        val = int(clean_digits)
        if val > 0:
            return val
    return None


def record_ad_spend(
    amount: int,
    date_str: Optional[str] = None,
    post_id: str = "",
    campaign_id: str = "",
    note: str = ""
) -> Dict[str, Any]:
    """
    Ghi nhận chi phí quảng cáo (theo ngày, bài viết hoặc chiến dịch).
    """
    from datetime import datetime
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    spends = load_ad_spends()
    entry = {
        "id": f"spend_{int(datetime.now().timestamp())}_{len(spends)+1}",
        "date": date_str,
        "amount": int(amount),
        "post_id": str(post_id).strip(),
        "campaign_id": str(campaign_id).strip(),
        "note": str(note).strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    spends.append(entry)
    save_ad_spends(spends)
    return entry


def get_ad_spend_total(start_date: str, end_date: str, post_id: Optional[str] = None) -> int:
    """Tính tổng chi phí quảng cáo trong khoảng thời gian (start_date <= date <= end_date)."""
    spends = load_ad_spends()
    total = 0
    for s in spends:
        d = str(s.get("date", ""))
        if start_date <= d <= end_date:
            if post_id and str(s.get("post_id", "")).strip() != str(post_id).strip():
                continue
            total += int(s.get("amount", 0))
    return total


def calculate_ad_performance(orders: List[Dict[str, Any]], start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Tính toán hiệu quả quảng cáo và chi phí trên đơn hàng (CPA, ROAS, chi tiết từng Post ID).
    """
    total_orders = len(orders)
    ad_orders: List[Dict[str, Any]] = []
    organic_orders: List[Dict[str, Any]] = []
    post_breakdown: Dict[str, Dict[str, Any]] = {}

    for o in orders:
        ad_src = o.get("ad_source")
        if ad_src and isinstance(ad_src, dict):
            ad_orders.append(o)
            p_id = str(ad_src.get("post_id") or "chua_ro_id").strip()
            camp_name = str(ad_src.get("campaign") or "Facebook Ads")
            if p_id not in post_breakdown:
                post_breakdown[p_id] = {
                    "campaign": camp_name,
                    "orders": 0,
                    "revenue": 0
                }
            post_breakdown[p_id]["orders"] += 1
            post_breakdown[p_id]["revenue"] += int(o.get("tong_tien", 0))
        else:
            organic_orders.append(o)

    total_ad_orders = len(ad_orders)
    total_organic_orders = len(organic_orders)
    ad_revenue = sum(int(o.get("tong_tien", 0)) for o in ad_orders)
    organic_revenue = sum(int(o.get("tong_tien", 0)) for o in organic_orders)
    total_revenue = ad_revenue + organic_revenue

    total_ad_spend = get_ad_spend_total(start_date, end_date)

    # Chi phí trung bình trên mỗi đơn hàng từ Ads (CPA)
    cpa = round(total_ad_spend / total_ad_orders) if total_ad_orders > 0 else 0
    # ROAS (Doanh thu từ Ads / Chi phí Ads)
    roas = round(ad_revenue / total_ad_spend, 2) if total_ad_spend > 0 else 0.0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_orders": total_orders,
        "ad_orders_count": total_ad_orders,
        "organic_orders_count": total_organic_orders,
        "ad_revenue": ad_revenue,
        "organic_revenue": organic_revenue,
        "total_revenue": total_revenue,
        "ad_spend": total_ad_spend,
        "cpa": cpa,
        "roas": roas,
        "post_breakdown": post_breakdown
    }
