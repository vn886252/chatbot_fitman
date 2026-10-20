import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.ad_service import resolve_ad_campaign, get_campaign_images
from app.services.customer_service import save_customer_profile, get_customer_profile, format_customer_memory_context
from app.services.order_service import save_order

client = TestClient(app)


def test_resolve_ad_campaign_by_ref():
    """Kiểm tra nhận diện chiến dịch qua mã ref từ Facebook Ads Manager."""
    # Test 1: ref = mau_46
    ref_data = {"ref": "mau_46", "source": "ADS"}
    camp = resolve_ad_campaign(ref_data)
    assert camp is not None
    assert "46" in camp["model_codes"]
    assert "47" in camp["model_codes"]
    assert len(camp["resolved_images"]) >= 1

    # Test 2: ref = quan_short
    ref_quan = {"ref": "quan_short", "source": "ADS"}
    camp_q = resolve_ad_campaign(ref_quan)
    assert camp_q is not None
    assert "quần" in camp_q["model_codes"]
    assert "quần" in camp_q["greeting_text"].lower()

    # Test 3: ref = basketball
    ref_bb = {"ref": "basketball", "source": "ADS"}
    camp_bb = resolve_ad_campaign(ref_bb)
    assert camp_bb is not None
    assert "B1" in camp_bb["model_codes"]
    assert "B2" in camp_bb["model_codes"]


def test_resolve_ad_campaign_by_post_id():
    """Kiểm tra nhận diện chiến dịch qua post_id bài viết Fanpage (khi chạy ads bài viết)."""
    # Giả lập tạm thời post_ids trong campaign
    from app.services.ad_service import load_ad_campaigns
    campaigns = load_ad_campaigns()
    for c in campaigns:
        if c["id"] == "basketball":
            c["post_ids"] = ["123456789_987654321"]
            break

    with patch("app.services.ad_service.load_ad_campaigns", return_value=campaigns):
        # Case 1: Facebook gửi post_id đầy đủ PAGEID_POSTID
        ref_full = {
            "source": "ADS",
            "ads_context_data": {"post_id": "123456789_987654321"}
        }
        camp1 = resolve_ad_campaign(ref_full)
        assert camp1 is not None
        assert camp1["id"] == "basketball"
        assert "B1" in camp1["model_codes"]

        # Case 2: Facebook gửi post_id chỉ gồm phần đuôi số bài viết
        ref_suffix = {
            "source": "ADS",
            "ads_context_data": {"post_id": "987654321"}
        }
        camp2 = resolve_ad_campaign(ref_suffix)
        assert camp2 is not None
        assert camp2["id"] == "basketball"


def test_resolve_ad_campaign_by_title_keyword():
    """Kiểm tra nhận diện chiến dịch qua từ khóa trong tiêu đề bài quảng cáo."""
    ref_data = {
        "source": "ADS",
        "ads_context_data": {
            "ad_title": "Bộ sưu tập Áo Mẫu 46 & 47 mới nhất",
            "photo_url": "https://example.com/ad_photo.jpg"
        }
    }
    camp = resolve_ad_campaign(ref_data)
    assert camp is not None
    assert "46" in camp["model_codes"]
    assert camp["photo_url"] == "https://example.com/ad_photo.jpg"


def test_customer_service_ad_tracking():
    """Kiểm tra lưu thông tin ad vào customer profile và inject vào prompt memory."""
    sender_id = "fb_user_ad_test_01"
    prof = save_customer_profile(
        sender_id,
        ten_khach_hang="Anh Hoàng",
        source="facebook_ads",
        ad_id="120288888888",
        ad_title="Áo CBUM Mẫu 46",
        ad_ref="mau_46",
        ad_campaign_name="Áo CBUM Mẫu 46 & 47",
        ad_models=["46", "47"]
    )
    assert prof["ad_ref"] == "mau_46"
    assert prof["ad_models"] == ["46", "47"]

    # Kiểm tra context memory sinh ra cho LLM
    mem = format_customer_memory_context(prof)
    assert "Áo CBUM Mẫu 46 & 47" in mem
    assert "46, 47" in mem


def test_order_creation_captures_ad_source():
    """Kiểm tra khi khách chốt đơn, thông tin chiến dịch Ads được tự động gắn vào đơn hàng."""
    sender_id = "fb_user_ad_buyer_02"
    save_customer_profile(
        sender_id,
        ten_khach_hang="Nguyễn Văn Ad",
        source="facebook_ads",
        ad_id="120299999999",
        ad_ref="mau_46",
        ad_campaign_name="Áo CBUM Mẫu 46 & 47",
        ad_models=["46", "47"]
    )

    order_payload = {
        "ten_khach_hang": "Nguyễn Văn Ad",
        "so_dien_thoai": "0987654321",
        "dia_chi": "456 Trần Phú, Q5, TP.HCM",
        "danh_sach_mon": ["Áo mẫu 46 (L)", "Áo mẫu 47 (L)"],
        "so_luong": 2,
        "tong_tien": 300000,
        "sender_id": sender_id
    }
    saved = save_order(order_payload)
    assert saved is not None
    assert "ad_source" in saved
    assert saved["ad_source"]["campaign"] == "Áo CBUM Mẫu 46 & 47"
    assert saved["ad_source"]["ad_ref"] == "mau_46"


@pytest.mark.asyncio
async def test_webhook_ad_referral_triggers_greeting_and_images():
    """Kiểm tra webhook nhận sự kiện referral từ Facebook Ads: gửi ảnh mẫu + gửi alert Telegram."""
    sender_id = "fb_user_ad_webhook_03"
    payload = {
        "object": "page",
        "entry": [{
            "messaging": [{
                "sender": {"id": sender_id},
                "recipient": {"id": "page_123"},
                "referral": {
                    "source": "ADS",
                    "ad_id": "12021111111111",
                    "ref": "mau_46",
                    "ads_context_data": {
                        "ad_title": "Áo CBUM Mẫu 46 & 47"
                    }
                }
            }]
        }]
    }

    with patch("app.routers.webhook.send_text_message", new_callable=AsyncMock) as mock_send_text, \
         patch("app.routers.webhook.send_image_message", new_callable=AsyncMock) as mock_send_img, \
         patch("app.services.telegram_service.send_ad_referral_alert", new_callable=AsyncMock) as mock_ad_alert:

        res = client.post("/webhook", json=payload)
        assert res.status_code == 200

        # Kiểm tra gửi chào đúng mẫu
        mock_send_text.assert_called_once()
        sent_text = mock_send_text.call_args[0][1]
        assert "quảng cáo" in sent_text.lower()
        assert "chiều cao và cân nặng" in sent_text.lower()

        # Kiểm tra gửi ảnh mẫu
        assert mock_send_img.call_count >= 1

        # Kiểm tra gửi Telegram alert cho chủ shop
        mock_ad_alert.assert_called_once()
        assert mock_ad_alert.call_args[1]["campaign_name"] == "Áo CBUM Mẫu 46 & 47"

        # Kiểm tra hồ sơ khách hàng đã được lưu
        prof = get_customer_profile(sender_id)
        assert prof is not None
        assert prof["ad_ref"] == "mau_46"
        assert prof["ad_campaign_name"] == "Áo CBUM Mẫu 46 & 47"


def test_basketball_three_post_ids():
    """Kiểm tra cả 3 Post ID thực tế của áo Basketball mà chủ shop cấu hình."""
    post_ids = ["1523979186418810", "1523987709751291", "1523986613084734"]
    for pid in post_ids:
        ref_data = {
            "source": "ADS",
            "ads_context_data": {
                "post_id": f"page123_{pid}"
            }
        }
        camp = resolve_ad_campaign(ref_data)
        assert camp is not None, f"Failed to resolve campaign for post {pid}"
        assert camp["id"] == "basketball"
        assert camp["post_id"] == f"page123_{pid}"
        assert "B1" in camp["model_codes"]
        assert "B2" in camp["model_codes"]
        assert len(camp["resolved_images"]) >= 1


def test_ad_spend_and_performance_metrics():
    """Kiểm tra ghi nhận chi phí ads, tính CPA trên đơn hàng và ROAS."""
    from app.services.ad_service import parse_currency_amount, record_ad_spend, calculate_ad_performance, AD_SPEND_FILE
    import os

    # Test parse tiền
    assert parse_currency_amount("200k") == 200000
    assert parse_currency_amount("200.000") == 200000
    assert parse_currency_amount("1.5tr") == 1500000
    assert parse_currency_amount("500000") == 500000

    # Test ghi nhận chi phí và tính metrics
    test_date = "2099-01-01"
    with patch("app.services.ad_service.load_ad_spends") as mock_load:
        mock_load.return_value = [
            {"date": test_date, "amount": 200000, "post_id": "1523979186418810"}
        ]

        mock_orders = [
            {
                "id": "ORD-001",
                "tong_tien": 300000,
                "ad_source": {
                    "campaign": "Áo Bóng Rổ Basketball B1 & B2",
                    "post_id": "1523979186418810"
                }
            },
            {
                "id": "ORD-002",
                "tong_tien": 300000,
                "ad_source": {
                    "campaign": "Áo Bóng Rổ Basketball B1 & B2",
                    "post_id": "1523979186418810"
                }
            },
            {
                "id": "ORD-003",
                "tong_tien": 200000
                # Đơn tự nhiên
            }
        ]

        perf = calculate_ad_performance(mock_orders, test_date, test_date)
        assert perf["total_orders"] == 3
        assert perf["ad_orders_count"] == 2
        assert perf["organic_orders_count"] == 1
        assert perf["ad_revenue"] == 600000
        assert perf["ad_spend"] == 200000
        # CPA = 200.000 / 2 = 100.000đ/đơn
        assert perf["cpa"] == 100000
        # ROAS = 600.000 / 200.000 = 3.0x
        assert perf["roas"] == 3.0
        assert "1523979186418810" in perf["post_breakdown"]


@pytest.mark.asyncio
async def test_telegram_ads_command_handler():
    """Kiểm tra lệnh /ads trên Telegram cập nhật chi phí và phản hồi CPA."""
    from app.services.telegram_service import handle_telegram_update
    from app.config import settings

    update = {
        "message": {
            "chat": {"id": str(settings.TELEGRAM_CHAT_ID)},
            "text": "/ads 1523979186418810 250k"
        }
    }

    with patch("app.services.telegram_service.send_telegram_message", new_callable=AsyncMock) as mock_send, \
         patch("app.services.ad_service.record_ad_spend") as mock_record:
        mock_send.return_value = True
        mock_record.return_value = {"id": "spend_mock", "amount": 250000}
        res = await handle_telegram_update(update)
        assert res is True
        mock_send.assert_called_once()
        sent_txt = mock_send.call_args[0][0]
        assert "ĐÃ GHI NHẬN CHI PHÍ ADS" in sent_txt
        assert "250.000đ" in sent_txt
        assert "1523979186418810" in sent_txt

