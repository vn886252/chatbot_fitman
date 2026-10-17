import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import io
import os
import json
import uuid
import random
import asyncio
import logging
from pathlib import Path
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import (
    TELEGRAM_BOT_TOKEN, 
    WORKFLOW_TEMPLATE_PATH, 
    COMFYUI_OUTPUT_DIR,
    HOST_IMAGE_NAME
)
from llm_agent import generate_script_and_prompt
from workflow_api import (
    upload_image, 
    execute_phase1_qwen, 
    execute_phase2_minimax,
    execute_refiner_qwen
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Luu trang thai phien lam viec theo user_id
user_sessions = {}
# Bo dem gom cac anh gui cung luc (Media Group Album)
media_group_buffers = {}

def prepare_image_for_telegram(img_bytes: bytes) -> io.BytesIO:
    """Nen nhe JPEG chat luong cao 95% de gui Telegram cuc nhanh, tranh loi TimedOut do mang cham"""
    try:
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        out_io = io.BytesIO()
        im.save(out_io, format="JPEG", quality=95, optimize=True)
        out_io.seek(0)
        out_io.name = "storyboard.jpg"
        return out_io
    except Exception:
        out_io = io.BytesIO(img_bytes)
        out_io.name = "storyboard.png"
def get_cropped_product_image(img_bytes: bytes, product_info: dict, is_back_view: bool) -> bytes:
    """
    Tu dong phat hien anh composite (chua 2 nguoi mau mat truoc va mat sau trong 1 anh)
    va cat goc phu hop de truyen cho Qwen lam tham chieu duy nhat.
    Loai bo triet de nguoi mau con lai, mu non va hinh xam tu anh goc.
    """
    try:
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = im.size
        
        crop_box = None
        if product_info and product_info.get("is_composite"):
            if is_back_view and "back_crop" in product_info:
                crop_box = product_info["back_crop"]
            elif not is_back_view and "front_crop" in product_info:
                crop_box = product_info["front_crop"]
        
        # Fallback heuristic neu la anh vuong hoac gan vuong va chua duoc danh dau composite
        if not crop_box and 0.8 <= (w / h) <= 1.25:
            # Heuristic cat 60% nua phai cho front, 60% nua trai cho back de tranh bi 2 nguoi
            if is_back_view:
                crop_box = [0.0, 0.0, 1.0, 0.65]
            else:
                crop_box = [0.0, 0.40, 1.0, 1.0]

        if crop_box and len(crop_box) == 4:
            ymin, xmin, ymax, xmax = crop_box
            
            # Loai bo phan dau (khuon mat ngoai & mu non/cap) de tranh Qwen copy mu hoac mat sai vao Host
            # Chi lay tu co ao xuong den vat ao de tap trung 100% vao form dang ao va graphic
            if ymin < 0.20 and (ymax - ymin) > 0.40:
                ymin = 0.20
            
            x1 = max(0, int(xmin * w))
            y1 = max(0, int(ymin * h))
            x2 = min(w, int(xmax * w))
            y2 = min(h, int(ymax * h))
            
            if (x2 - x1) > 50 and (y2 - y1) > 50:
                cropped = im.crop((x1, y1, x2, y2))
                # Upscale neu nho hon 768px de dam bao chat luong cao cho vision encoder Qwen
                if cropped.width < 768 or cropped.height < 768:
                    scale = max(768 / cropped.width, 768 / cropped.height)
                    new_w = int(cropped.width * scale)
                    new_h = int(cropped.height * scale)
                    cropped = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                out_io = io.BytesIO()
                cropped.save(out_io, format="PNG")
                return out_io.getvalue()
    except Exception as e:
        logger.warning(f"Loi khi crop anh san pham: {e}")
        
    return img_bytes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lenh /start chao mung va huong dan quy trinh 2 buoc an toan VRAM"""
    welcome_text = (
        "🎬 **Chào mừng bạn đến với Fitman AI Video Automation!**\n\n"
        "✨ **Tính năng Storyboard 360° & Tạo Video chuyển cảnh đỉnh cao:**\n"
        "• Bạn có thể gửi **1 ảnh hoặc 2-3 ảnh** trang phục kèm mô tả ý tưởng!\n"
        "• **Quy chuẩn 360°:** Mỗi chiếc áo đều được tạo đủ **Mặt trước (Front View)** và **Mặt sau (Back View)** để MiniMax có đủ ảnh tham chiếu khi xoay người/tiếp đất!\n"
        "  - Gửi 1 áo ➡️ Tạo 2 ảnh Storyboard (Áo 1 Trước & Sau).\n"
        "  - Gửi 2 áo ➡️ Tạo 4 ảnh Storyboard (Áo 1 Trước/Sau & Áo 2 Trước/Sau).\n\n"
        "🚀 **Duyệt & Tạo lại từng ảnh linh hoạt:**\n"
        "• Bạn có thể bấm **Tạo lại riêng từng ảnh** (ví dụ chỉ tạo lại Ảnh 1 nếu chưa ưng ý) mà không làm mất các ảnh khác!\n"
        "• Khi duyệt cả bộ ảnh xong ➡️ Bắt đầu render video MiniMax H3 mượt mà!\n\n"
        "📥 **Lấy clip nhanh bất cứ lúc nào:** Gõ lệnh `/layclip` để tải video mới nhất vừa render trong máy về Telegram.\n\n"
        "🛡️ **Bảo vệ 16GB VRAM:** Tách biệt 2 phase hoàn toàn, tuyệt đối không lo tràn bộ nhớ!\n\n"
        "👉 *Hãy gửi 1 hoặc 2-3 tấm ảnh trang phục kèm mô tả ý tưởng của bạn để bắt đầu!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

def split_video_into_clips(video_path: Path) -> list[tuple[str, bytes, float]]:
    """Tach video thanh 2 phan doan bang ffmpeg lossless khong can encode lai"""
    try:
        import subprocess
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        total_sec = total_frames / fps
        cap.release()

        mid_sec = total_sec / 2.0
        temp_id = uuid.uuid4().hex[:6]
        clip1_path = video_path.parent / f"temp_{temp_id}_part1.mp4"
        clip2_path = video_path.parent / f"temp_{temp_id}_part2.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-ss", "00:00:00", "-to", f"{mid_sec:.2f}", "-c", "copy", str(clip1_path),
            "-ss", f"{mid_sec:.2f}", "-to", f"{total_sec:.2f}", "-c", "copy", str(clip2_path)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        results = []
        if clip1_path.is_file():
            with open(clip1_path, "rb") as f:
                results.append((f"PhanDoan1_TrangPhuc1_{mid_sec:.0f}s.mp4", f.read(), mid_sec))
            clip1_path.unlink(missing_ok=True)
        if clip2_path.is_file():
            with open(clip2_path, "rb") as f:
                results.append((f"PhanDoan2_TrangPhuc2_{(total_sec - mid_sec):.0f}s.mp4", f.read(), total_sec - mid_sec))
            clip2_path.unlink(missing_ok=True)
        return results
    except Exception as e:
        logger.error(f"Lỗi khi tách clip bằng ffmpeg: {e}", exc_info=True)
        return []

async def layclip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gui ngay file video .mp4 gan nhat trong output cho nguoi dung"""
    status_msg = await update.message.reply_text("🔍 Đang tìm file video clip thành phẩm gần nhất...")
    try:
        mp4_files = sorted(
            COMFYUI_OUTPUT_DIR.glob("*.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not mp4_files:
            await status_msg.edit_text("⚠️ Chưa tìm thấy file video nào trong thư mục output.")
            return

        latest_video = mp4_files[0]
        size_mb = latest_video.stat().st_size / (1024 * 1024)
        await status_msg.edit_text(f"🚀 Đang gửi video `{latest_video.name}` ({size_mb:.1f} MB) về Telegram...", parse_mode="Markdown")

        with open(latest_video, "rb") as f:
            video_bytes = f.read()

        video_io = io.BytesIO(video_bytes)
        video_io.name = latest_video.name

        chat_id = update.effective_chat.id
        split_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✂️ Tách Thành 2 Clip Rời (5s / clip)", callback_data="btn_split_clips")]
        ])
        await context.bot.send_video(
            chat_id=chat_id,
            video=video_io,
            caption=(
                f"🎬 **Video thành phẩm hoàn chỉnh từ MiniMax H3!**\n"
                f"📁 File: `{latest_video.name}` ({size_mb:.1f} MB)\n"
                f"✨ 1 Video liền mạch 10s chuyển cảnh mượt mà giữa các trang phục.\n"
                f"👉 Bấm nút bên dưới nếu bạn muốn lấy 2 clip 5s rời để tự ghép CapCut:"
            ),
            reply_markup=split_kb,
            read_timeout=180.0,
            write_timeout=180.0
        )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Lỗi gửi clip qua /layclip: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Lỗi khi gửi clip: {str(e)}")

async def tachclip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lenh /tachclip: Tu dong cat tach video 10s thanh 2 clip roi 5s"""
    status_msg = await update.message.reply_text("✂️ Đang tách video thành 2 clip phân đoạn rời (5s / clip)...")
    try:
        mp4_files = sorted(
            COMFYUI_OUTPUT_DIR.glob("*.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not mp4_files:
            await status_msg.edit_text("⚠️ Chưa tìm thấy video nào để tách.")
            return

        latest_video = mp4_files[0]
        clips = split_video_into_clips(latest_video)
        if not clips:
            await status_msg.edit_text("❌ Không thể tách video.")
            return

        chat_id = update.effective_chat.id
        for idx, (c_name, c_bytes, c_dur) in enumerate(clips):
            c_io = io.BytesIO(c_bytes)
            c_io.name = c_name
            outfit_num = idx + 1
            c_caption = (
                f"🎬 **Phân đoạn {idx+1}: Trang phục {outfit_num} ({c_dur:.1f}s)**\n"
                f"📁 File: `{c_name}`\n"
                f"✨ Dùng để edit trên CapCut / Premiere."
            )
            await context.bot.send_video(
                chat_id=chat_id,
                video=c_io,
                caption=c_caption,
                read_timeout=180.0,
                write_timeout=180.0
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Lỗi lệnh /tachclip: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Lỗi tách clip: {str(e)}")

def build_approval_keyboard(num_storyboards: int, current_duration: float, video_quality: str = "720p") -> list:
    """Tao ban phim duyet anh kem cac nut doi thoi luong, chat luong, tao lai tung anh hoac tao lai tat ca"""
    action_label = f"🚀 2. Duyệt Cả {num_storyboards} Ảnh & Bắt Đầu Render Video ({current_duration:.0f}s - {video_quality.upper()})" if num_storyboards > 1 else f"🚀 2. Duyệt Ảnh & Bắt Đầu Render Video ({current_duration:.0f}s - {video_quality.upper()})"
    
    keyboard = [
        [InlineKeyboardButton(action_label, callback_data="btn_run_phase2_from_image")],
        [InlineKeyboardButton("✨ Nâng Cấp Chân Thực 1080p (LoRA Lenovo)", callback_data="btn_refine_lenovo_1080p")],
        [
            InlineKeyboardButton(f"{'✅ ' if current_duration == 10 else ''}⏱ 10s", callback_data="btn_dur_10"),
            InlineKeyboardButton(f"{'✅ ' if current_duration == 12 else ''}⏱ 12s", callback_data="btn_dur_12"),
            InlineKeyboardButton(f"{'✅ ' if current_duration == 15 else ''}⏱ 15s", callback_data="btn_dur_15"),
        ],
        [
            InlineKeyboardButton(f"🎬 Video: {'✅ 720p (Nhanh & Mượt)' if video_quality == '720p' else '720p'}", callback_data="btn_quality_720p"),
            InlineKeyboardButton(f"🎬 Video: {'✅ 1080p' if video_quality == '1080p' else '1080p'}", callback_data="btn_quality_1080p"),
        ],
    ]

    # Nut tao lai tung anh rieng biet (2 nut tren 1 hang)
    single_reroll_rows = []
    current_row = []
    for i in range(num_storyboards):
        shirt_num = (i // 2) + 1
        view_label = "Trước" if i % 2 == 0 else "Sau"
        btn_text = f"🔄 Tạo lại Ảnh {i+1} (Áo {shirt_num} - {view_label})"
        current_row.append(InlineKeyboardButton(btn_text, callback_data=f"btn_reroll_single_{i}"))
        if len(current_row) == 2:
            single_reroll_rows.append(current_row)
            current_row = []
    if current_row:
        single_reroll_rows.append(current_row)

    keyboard.extend(single_reroll_rows)
    keyboard.append([InlineKeyboardButton(f"🔄 Đổi Seed Tạo Lại Toàn Bộ {num_storyboards} Ảnh", callback_data="btn_reroll_image")])
    keyboard.append([
        InlineKeyboardButton("✍️ Viết Lại Kịch Bản Khác", callback_data="btn_rewrite"),
        InlineKeyboardButton("❌ Hủy Bỏ", callback_data="btn_cancel")
    ])
    return keyboard

async def process_photos_submission(user_id: int, photos: list[bytes], caption: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Xu ly danh sach anh gui len (1 anh hoac nhieu anh)"""
    num_photos = len(photos)
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🧠 Antigravity đang phân tích {num_photos} trang phục và viết kịch bản 360° (Mặt trước & Mặt sau)..."
    )

    try:
        # Goi Antigravity tao kich ban va prompt cho tung clip
        result = await asyncio.to_thread(generate_script_and_prompt, photos, caption)
        duration = float(result.get("duration", 10.0))
        qwen_prompts = result.get("qwen_prompts", [result.get("qwen_prompt")])
        num_storyboards = len(qwen_prompts)

        user_sessions[user_id] = {
            "image_bytes_list": photos,
            "products": result.get("products", []),
            "vietnamese_script": result["vietnamese_script"],
            "qwen_prompts": qwen_prompts,
            "minimax_prompt": result["minimax_prompt"],
            "caption": caption,
            "duration": duration,
            "video_quality": "720p",
            "phase1_bytes_list": [],
            "phase1_image_names": [],
            "chat_id": chat_id
        }

        btn_label = f"📸 1. Tạo {num_storyboards} Ảnh Storyboard Để Duyệt (Qwen)"
        keyboard = [
            [InlineKeyboardButton(btn_label, callback_data="btn_run_phase1_only")],
            [
                InlineKeyboardButton(f"{'✅ ' if duration == 10 else ''}⏱ 10s", callback_data="btn_dur_10"),
                InlineKeyboardButton(f"{'✅ ' if duration == 12 else ''}⏱ 12s", callback_data="btn_dur_12"),
                InlineKeyboardButton(f"{'✅ ' if duration == 15 else ''}⏱ 15s", callback_data="btn_dur_15"),
            ],
            [
                InlineKeyboardButton("🎬 Video: ✅ 720p (Nhanh & Mượt)", callback_data="btn_quality_720p"),
                InlineKeyboardButton("🎬 Video: 1080p", callback_data="btn_quality_1080p"),
            ],
            [InlineKeyboardButton("✍️ Viết Lại Kịch Bản Khác", callback_data="btn_rewrite"),
             InlineKeyboardButton("❌ Hủy Bỏ", callback_data="btn_cancel")]
        ]

        title = f"🎬 **KỊCH BẢN CHUYỂN CẢNH {num_storyboards} STORYBOARDS ({num_photos} TRANG PHỤC):**" if num_photos > 1 else f"🎬 **KỊCH BẢN ĐỀ XUẤT ({num_storyboards} STORYBOARDS - {duration:.0f}S):**"
        msg_body = (
            f"{title}\n\n"
            f"{result['vietnamese_script']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Model:** *Chàng Host thể thao châu Á từ <image1> (khóa khuôn mặt & không hình xăm 100%)*\n"
            f"⏱ **Thời lượng clip:** {duration:.0f} giây (có thể chọn nút 10s/12s/15s ở dưới)\n"
            f"🛡️ **Quy trình Storyboard 360°:** Bot sẽ tạo đủ {num_storyboards} ảnh Storyboard (mỗi áo có đủ Mặt trước & Mặt sau) để bạn duyệt trước ➡️ Duyệt xong mới render video MiniMax!"
        )

        await status_msg.delete()
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg_body,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Lỗi khi xử lý ảnh: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Đã xảy ra lỗi: {str(e)}")

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bat anh nguoi dung gui: Ho tro ca gui 1 anh hoac gui Album nhieu anh cung luc"""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    user_caption = update.message.caption or ""
    media_group_id = update.message.media_group_id

    photo_file = await photo.get_file()
    img_buffer = io.BytesIO()
    await photo_file.download_to_memory(img_buffer)
    image_bytes = img_buffer.getvalue()

    if media_group_id:
        if media_group_id not in media_group_buffers:
            media_group_buffers[media_group_id] = {
                "photos": [image_bytes],
                "caption": user_caption,
                "chat_id": update.effective_chat.id,
                "user_id": user_id,
                "task": None
            }
        else:
            media_group_buffers[media_group_id]["photos"].append(image_bytes)
            if user_caption:
                media_group_buffers[media_group_id]["caption"] = user_caption

        # Debounce: Cho 1.2s de gom het anh trong album
        existing_task = media_group_buffers[media_group_id].get("task")
        if existing_task and not existing_task.done():
            existing_task.cancel()

        async def delayed_process(mg_id):
            try:
                await asyncio.sleep(1.2)
                entry = media_group_buffers.pop(mg_id, None)
                if entry:
                    await process_photos_submission(
                        user_id=entry["user_id"],
                        photos=entry["photos"],
                        caption=entry["caption"],
                        chat_id=entry["chat_id"],
                        context=context
                    )
            except asyncio.CancelledError:
                pass

        media_group_buffers[media_group_id]["task"] = asyncio.create_task(delayed_process(media_group_id))
    else:
        # 1 anh don le
        await process_photos_submission(
            user_id=user_id,
            photos=[image_bytes],
            caption=user_caption,
            chat_id=update.effective_chat.id,
            context=context
        )

async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xu ly nut bam tren Telegram"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    action = query.data

    # Xu ly nut lay lai video vua render xong ma khong can session ton tai
    if action == "btn_fetch_latest_video":
        await query.message.reply_text("📥 Đang tìm video mới nhất trong máy để gửi cho bạn...")
        try:
            mp4_files = sorted(
                COMFYUI_OUTPUT_DIR.glob("*.mp4"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not mp4_files:
                await query.message.reply_text("⚠️ Chưa tìm thấy file video nào.")
                return

            latest_video = mp4_files[0]
            size_mb = latest_video.stat().st_size / (1024 * 1024)
            with open(latest_video, "rb") as f:
                v_bytes = f.read()

            v_io = io.BytesIO(v_bytes)
            v_io.name = latest_video.name
            chat_id = update.effective_chat.id
            await context.bot.send_video(
                chat_id=chat_id,
                video=v_io,
                caption=f"🎬 **Video thành phẩm MiniMax H3!**\n📁 File: `{latest_video.name}` ({size_mb:.1f} MB)",
                read_timeout=180.0,
                write_timeout=180.0
            )
        except Exception as e:
            await query.message.reply_text(f"❌ Lỗi gửi video: {str(e)}")
    # Xu ly nut tach clip
    if action == "btn_split_clips":
        await query.message.reply_text("✂️ Đang dùng ffmpeg tách video thành 2 clip phân đoạn rời (5s / clip)...")
        try:
            mp4_files = sorted(
                COMFYUI_OUTPUT_DIR.glob("*.mp4"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not mp4_files:
                await query.message.reply_text("⚠️ Chưa tìm thấy file video nào để tách.")
                return

            latest_video = mp4_files[0]
            clips = split_video_into_clips(latest_video)
            if not clips:
                await query.message.reply_text("❌ Không thể tách video.")
                return

            chat_id = update.effective_chat.id
            for idx, (c_name, c_bytes, c_dur) in enumerate(clips):
                c_io = io.BytesIO(c_bytes)
                c_io.name = c_name
                outfit_num = idx + 1
                c_caption = (
                    f"🎬 **Phân đoạn {idx+1}: Trang phục {outfit_num} ({c_dur:.1f}s)**\n"
                    f"📁 File: `{c_name}`\n"
                    f"✨ Đã tách rời để bạn tiện kéo vào CapCut / Premiere biên tập thêm!"
                )
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=c_io,
                    caption=c_caption,
                    read_timeout=180.0,
                    write_timeout=180.0
                )
        except Exception as e:
            await query.message.reply_text(f"❌ Lỗi tách clip: {str(e)}")
        return

    if user_id not in user_sessions:
        await query.edit_message_text("⚠️ Phiên làm việc đã hết hạn. Vui lòng gửi lại ảnh trang phục hoặc gõ `/layclip` để nhận video mới nhất!")
        return

    session = user_sessions[user_id]
    image_list = session["image_bytes_list"]
    qwen_prompts = session.get("qwen_prompts", [])
    num_storyboards = len(session.get("phase1_image_names", [])) or len(qwen_prompts)

    # --- DOI NHANH THOI LUONG VIDEO (10S / 12S / 15S) HOAC DO PHAN GIAI (720P / 1080P) ---
    if action in ["btn_dur_10", "btn_dur_12", "btn_dur_15", "btn_dur_20"]:
        new_dur = 10.0 if action == "btn_dur_10" else (12.0 if action == "btn_dur_12" else (15.0 if action == "btn_dur_15" else 20.0))
        session["duration"] = new_dur
        await query.message.reply_text(f"⏱ Đã đổi thời lượng video thành **{new_dur:.0f} giây**!")
        
        if session.get("phase1_image_names"):
            new_kb = build_approval_keyboard(len(session["phase1_image_names"]), new_dur, session.get("video_quality", "720p"))
            await query.message.reply_text("👉 Chọn thao tác tiếp theo:", reply_markup=InlineKeyboardMarkup(new_kb))
        return

    if action in ["btn_quality_720p", "btn_quality_1080p"]:
        new_q = "720p" if action == "btn_quality_720p" else "1080p"
        session["video_quality"] = new_q
        await query.message.reply_text(f"🎬 Đã chọn độ phân giải Video: **{new_q.upper()}** (9:16 dọc)!")
        
        if session.get("phase1_image_names"):
            new_kb = build_approval_keyboard(len(session["phase1_image_names"]), session["duration"], new_q)
            await query.message.reply_text("👉 Chọn thao tác tiếp theo:", reply_markup=InlineKeyboardMarkup(new_kb))
        return

    # --- 1.0 NANG CAP CHAN THUC 1080P VOI LORA LENOVO (REFINER PASS) ---
    if action == "btn_refine_lenovo_1080p":
        if not session.get("phase1_image_names"):
            await query.message.reply_text("⚠️ Chưa có ảnh Storyboard nào trong phiên để nâng cấp.")
            return

        num_sb = len(session["phase1_image_names"])
        progress_msg = await query.message.reply_text(
            f"✨ **BẮT ĐẦU NÂNG CẤP CHÂN THỰC 1080P (LORA LENOVO - 1088x1920):**\n"
            f"Đang phủ vân da người thật, dệt sợi vải cotton & khử sạch AI look cho {num_sb} ảnh...\n"
            f"(Denoise 0.28 giữ nguyên vẹn 100% graphic, màu áo, form áo và bối cảnh)"
        )

        loop = asyncio.get_running_loop()
        def sync_status_update(text):
            asyncio.run_coroutine_threadsafe(progress_msg.edit_text(text), loop)

        def run_refiner_all():
            refined_bytes = []
            refined_names = []
            for idx, base_img_name in enumerate(session["phase1_image_names"]):
                client_id = str(uuid.uuid4())
                shirt_num = (idx // 2) + 1
                view_label = "Mặt trước" if idx % 2 == 0 else "Mặt sau"
                sync_status_update(f"✨ Đang nâng cấp chân thực Storyboard {idx+1}/{num_sb} (Áo {shirt_num} - {view_label})...")
                prompt_text = session["qwen_prompts"][idx] if idx < len(session.get("qwen_prompts", [])) else ""
                b, name = execute_refiner_qwen(base_img_name, client_id, prompt_text=prompt_text, lora_strength=0.65, denoise=0.28, status_callback=sync_status_update)
                refined_bytes.append(b)
                refined_names.append(name)
            return refined_bytes, refined_names

        try:
            r_bytes, r_names = await asyncio.to_thread(run_refiner_all)
            session["phase1_bytes_list"] = r_bytes
            session["phase1_image_names"] = r_names

            await progress_msg.edit_text("🎉 **Hoàn thành nâng cấp! Bộ ảnh đã đạt độ phân giải 1088x1920 và chân thực như ảnh chụp máy cơ.**")

            for idx, b in enumerate(r_bytes):
                shirt_num = (idx // 2) + 1
                view_label = "Mặt trước (Front View)" if idx % 2 == 0 else "Mặt sau (Back View)"
                caption_text = (
                    f"✨ **Storyboard {idx+1}/{num_sb} (1080p REFINED - Áo {shirt_num} - {view_label}):**\n"
                    f"• Nâng cấp với LoRA Lenovo (Khử AI look 100%).\n"
                    f"• Vân da, vân vải cotton thật & graphic sắc nét 8K.\n"
                    f"• Độ phân giải: 1088x1920 (9:16 dọc)."
                )
                photo_stream = prepare_image_for_telegram(b)
                await query.message.reply_photo(photo=photo_stream, caption=caption_text)

            next_kb = build_approval_keyboard(num_sb, session["duration"], session.get("video_quality", "720p"))
            await query.message.reply_text(
                "👉 Ảnh Storyboard đã được nâng cấp độ chân thực tối đa! Bạn có thể duyệt để bắt đầu render video:",
                reply_markup=InlineKeyboardMarkup(next_kb)
            )
        except Exception as e:
            logger.error(f"Lỗi nâng cấp refiner 1080p: {e}", exc_info=True)
            await progress_msg.edit_text(f"❌ Lỗi khi nâng cấp chân thực: {str(e)}")
        return

    # --- 1.1 TAO LAI RIENG 1 ANH STORYBOARD (GRANULAR SINGLE RE-ROLL) ---
    if action.startswith("btn_reroll_single_"):
        target_idx = int(action.replace("btn_reroll_single_", ""))
        total_sb = len(session.get("qwen_prompts", []))
        if target_idx >= total_sb:
            await query.message.reply_text("⚠️ Ảnh cần tạo lại không hợp lệ.")
            return

        shirt_idx = target_idx // 2 if (target_idx // 2) < len(image_list) else 0
        view_label = "Mặt trước (Front View)" if target_idx % 2 == 0 else "Mặt sau (Back View)"
        shirt_num = (target_idx // 2) + 1

        await query.message.reply_text(
            f"🔄 **Đang tạo lại riêng Storyboard {target_idx+1}/{total_sb} (Áo {shirt_num} - {view_label})...**\n"
            f"(Các ảnh Storyboard khác được giữ nguyên 100%)"
        )
        progress_msg = await query.message.reply_text(f"⏳ Đang vẽ lại Storyboard {target_idx+1} với Seed mới...")

        loop = asyncio.get_running_loop()
        def sync_status_update(text):
            asyncio.run_coroutine_threadsafe(progress_msg.edit_text(text), loop)

        def run_phase1_single():
            with open(WORKFLOW_TEMPLATE_PATH, "r", encoding="utf-8") as f:
                raw_ui = json.load(f)

            prompt_text = session["qwen_prompts"][target_idx]
            img_b = image_list[shirt_idx]
            is_back = (target_idx % 2 != 0)
            products = session.get("products", [])
            prod_info = products[shirt_idx] if (products and shirt_idx < len(products)) else {}
            img_b_cropped = get_cropped_product_image(img_b, prod_info, is_back)

            img_filename = f"prod_clip_{target_idx+1}_reroll_{uuid.uuid4().hex[:6]}.png"
            uploaded_name = upload_image(img_b_cropped, img_filename)
            client_id = str(uuid.uuid4())
            new_seed = random.randint(1, 10**14)

            b, name = execute_phase1_qwen(raw_ui, uploaded_name, prompt_text, client_id, seed=new_seed, status_callback=sync_status_update)
            return b, name

        try:
            new_b, new_name = await asyncio.to_thread(run_phase1_single)

            if "phase1_bytes_list" in session and len(session["phase1_bytes_list"]) > target_idx:
                session["phase1_bytes_list"][target_idx] = new_b
            if "phase1_image_names" in session and len(session["phase1_image_names"]) > target_idx:
                session["phase1_image_names"][target_idx] = new_name

            await progress_msg.edit_text(f"🎉 **Đã tạo lại xong Storyboard {target_idx+1}/{total_sb}!**")

            caption_text = (
                f"📸 **Storyboard {target_idx+1}/{total_sb} (MỚI - Áo {shirt_num} - {view_label}):**\n"
                f"• Bối cảnh: Chuẩn xác theo kịch bản (1080x1920 9:16).\n"
                f"• Dùng làm reference `<Picture {target_idx+1}>`.\n"
                f"• Da sạch tự nhiên 100% không hình xăm, không mũ nón."
            )
            photo_stream = prepare_image_for_telegram(new_b)
            await query.message.reply_photo(photo=photo_stream, caption=caption_text)

            next_keyboard = build_approval_keyboard(total_sb, session["duration"], session.get("video_quality", "720p"))
            await query.message.reply_text(
                f"👉 Đã cập nhật ảnh {target_idx+1}. Bạn có thể duyệt để render video hoặc tiếp tục bấm tạo lại ảnh khác nếu cần:",
                reply_markup=InlineKeyboardMarkup(next_keyboard)
            )
        except Exception as e:
            logger.error(f"Lỗi tạo lại ảnh {target_idx+1}: {e}", exc_info=True)
            await progress_msg.edit_text(f"❌ Lỗi khi tạo lại ảnh {target_idx+1}:\n`{str(e)}`", parse_mode="Markdown")
        return

    # --- 1.2 TAO TOAN BO ANH STORYBOARD CHO CAC CLIP (PHASE 1 QWEN) ---
    if action in ["btn_run_phase1_only", "btn_reroll_image"]:
        is_reroll = (action == "btn_reroll_image")
        num_storyboards = len(qwen_prompts)
        title_text = f"🔄 Đang đổi Seed và tạo lại toàn bộ {num_storyboards} ảnh Storyboard..." if is_reroll else f"📸 BẮT ĐẦU GIAI ĐOẠN 1: TẠO {num_storyboards} ẢNH STORYBOARD 360° (QWEN)..."
        await query.message.reply_text(f"{title_text}\n(Group Video MiniMax đã bypass 100% để bảo vệ 16GB VRAM)")
        progress_msg = await query.message.reply_text(f"⏳ Đang khóa mặt Host châu Á và chuẩn bị tạo {num_storyboards} ảnh Storyboard (Mặt trước & Mặt sau)...")

        loop = asyncio.get_running_loop()
        def sync_status_update(text):
            asyncio.run_coroutine_threadsafe(progress_msg.edit_text(text), loop)

        def run_phase1_all():
            with open(WORKFLOW_TEMPLATE_PATH, "r", encoding="utf-8") as f:
                raw_ui = json.load(f)

            generated_bytes = []
            generated_names = []

            for idx, prompt_text in enumerate(qwen_prompts):
                # Moi ao gom 2 goc nhin: Front va Back
                shirt_idx = idx // 2 if (idx // 2) < len(image_list) else 0
                img_b = image_list[shirt_idx]
                is_back = (idx % 2 != 0)
                products = session.get("products", [])
                prod_info = products[shirt_idx] if (products and shirt_idx < len(products)) else {}
                img_b_cropped = get_cropped_product_image(img_b, prod_info, is_back)

                img_filename = f"prod_clip_{idx+1}_{uuid.uuid4().hex[:6]}.png"
                uploaded_name = upload_image(img_b_cropped, img_filename)
                client_id = str(uuid.uuid4())
                new_seed = random.randint(1, 10**14) if is_reroll else None

                shirt_num = (idx // 2) + 1
                view_label = "Mặt trước" if idx % 2 == 0 else "Mặt sau"
                sync_status_update(f"📸 Đang tạo Storyboard {idx+1}/{num_storyboards} (Áo {shirt_num} - {view_label})...")
                b, name = execute_phase1_qwen(raw_ui, uploaded_name, prompt_text, client_id, seed=new_seed, status_callback=sync_status_update)
                generated_bytes.append(b)
                generated_names.append(name)

            return generated_bytes, generated_names

        try:
            bytes_list, names_list = await asyncio.to_thread(run_phase1_all)
            session["phase1_bytes_list"] = bytes_list
            session["phase1_image_names"] = names_list

            await progress_msg.edit_text("🎉 **Hoàn thành Phase 1!** Đã giải phóng model Qwen khỏi VRAM.")

            # Gui tung anh Storyboard ve Telegram kem co che retry chong Timeout
            for idx, b in enumerate(bytes_list):
                shirt_num = (idx // 2) + 1
                view_label = "Mặt trước (Front View)" if idx % 2 == 0 else "Mặt sau (Back View)"
                caption_text = (
                    f"📸 **Storyboard {idx+1}/{num_storyboards} (Áo {shirt_num} - {view_label}):**\n"
                    f"• Bối cảnh: Chuẩn xác theo kịch bản video (1080x1920 9:16).\n"
                    f"• Host châu Á (Dùng làm reference `<Picture {idx+1}>`).\n"
                    f"• Da sạch tự nhiên 100% không hình xăm, không mũ nón."
                )
                
                # Retry gui anh len Telegram toi da 3 lan
                for attempt in range(3):
                    try:
                        photo_stream = prepare_image_for_telegram(b)
                        await query.message.reply_photo(photo=photo_stream, caption=caption_text)
                        break
                    except Exception as upload_err:
                        if attempt == 2:
                            logger.error(f"Lỗi gửi ảnh Storyboard {idx+1}: {upload_err}")
                            raise upload_err
                        await asyncio.sleep(2)

            # Ban phim duyet anh kem cac nut tao lai tung anh hoac tao lai tat ca
            next_keyboard = build_approval_keyboard(num_storyboards, session["duration"], session.get("video_quality", "720p"))

            guide_msg = (
                f"👉 **Bạn hãy xem kỹ {num_storyboards} ảnh Storyboard bên trên:**\n"
                "• Đã có đủ ảnh **Mặt trước** và **Mặt sau** của từng chiếc áo để MiniMax ghép chuyển động chuẩn 360°!\n"
                "• **Nếu có ảnh nào chưa ưng ý:** Bạn bấm nút `[🔄 Tạo lại Ảnh X]` tương ứng bên dưới để vẽ lại riêng ảnh đó (các ảnh khác giữ nguyên 100%).\n"
                f"• **Nếu đã ưng ý toàn bộ:** Bấm **[🚀 2. Duyệt Cả {num_storyboards} Ảnh & Bắt Đầu Render Video ({session['duration']:.0f}s)]** để MiniMax render video hoàn chỉnh!\n"
                "• Có thể đổi thời lượng (10s, 12s, 15s) hoặc độ phân giải (720p, 1080p) bất cứ lúc nào."
            )
            await query.message.reply_text(guide_msg, reply_markup=InlineKeyboardMarkup(next_keyboard))

        except Exception as e:
            logger.error(f"Lỗi Phase 1: {e}", exc_info=True)
            await progress_msg.edit_text(f"❌ Lỗi khi tạo ảnh Qwen:\n`{str(e)}`", parse_mode="Markdown")

    # --- 2. CHAY GIAI DOAN 2 TU CAC ANH DA DUYET ---
    elif action == "btn_run_phase2_from_image":
        if not session.get("phase1_image_names"):
            await query.message.reply_text("⚠️ Chưa có ảnh storyboard được tạo. Hãy bấm tạo ảnh trước!")
            return

        still_names = session["phase1_image_names"]
        dur = session["duration"]
        video_q = session.get("video_quality", "720p")
        await query.message.reply_text(
            f"🚀 **BẮT ĐẦU GIAI ĐOẠN 2: TẠO VIDEO MINIMAX ({dur:.0f}S - {video_q.upper()})**\n"
            f"• Ghép nối các Clip theo kịch bản mượt mà bằng {len(still_names)} ảnh reference (<Picture 1>, <Picture 2>...).\n"
            f"• Nắm rõ visual 360° cả mặt trước lẫn mặt sau của các trang phục, không lo biến dạng hay đoán mò!\n"
            f"• Độ phân giải: {video_q.upper()} (9:16 dọc) - Tối ưu an toàn 16GB VRAM, render mượt và chống tràn bộ nhớ.\n"
            "(Qwen đã giải phóng 100%, toàn bộ VRAM dành cho MiniMax H3)..."
        )
        progress_msg = await query.message.reply_text("⏳ Đang chuẩn bị nạp model MiniMax H3...")

        loop = asyncio.get_running_loop()
        def sync_status_update(text):
            asyncio.run_coroutine_threadsafe(progress_msg.edit_text(text), loop)

        def run_phase2():
            with open(WORKFLOW_TEMPLATE_PATH, "r", encoding="utf-8") as f:
                raw_ui = json.load(f)
            client_id = str(uuid.uuid4())
            return execute_phase2_minimax(
                raw_ui=raw_ui,
                still_image_names=still_names,
                video_prompt=session["minimax_prompt"],
                duration=dur,
                client_id=client_id,
                video_quality=session.get("video_quality", "720p"),
                status_callback=sync_status_update
            )

        try:
            video_bytes = await asyncio.to_thread(run_phase2)
            await progress_msg.edit_text("🎉 **Render Video thành công 100%!** Đang gửi video về Telegram...")

            video_io = io.BytesIO(video_bytes)
            video_io.name = "host_transition_video.mp4"

            trans_desc = f"Đã ghép nối chuyển cảnh mượt mà qua {len(still_names)} góc nhìn/trang phục kịch bản!" if len(still_names) > 1 else "Video thương mại đỉnh cao!"

            caption_msg = (
                f"🎬 **Video {dur:.0f}s ({session.get('video_quality', '720p').upper()} 9:16) hoàn chỉnh từ MiniMax H3!**\n\n"
                f"✨ {trans_desc}\n"
                f"👤 Host cơ bắp đồng nhất qua {len(still_names)} góc nhìn mặt trước & mặt sau trong cùng bối cảnh kịch bản.\n"
                "🛡️ Độ phân giải 720p/1080p tối ưu, tuyệt đối không lo tràn VRAM 16GB.\n"
                "👉 Bạn có thể đưa vào CapCut / Premiere để chèn thêm âm thanh, nhạc nền!"
            )

            chat_id = session.get("chat_id", update.effective_chat.id)
            split_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✂️ Tách Thành 2 Clip Rời (5s / clip)", callback_data="btn_split_clips")]
            ])
            for attempt in range(3):
                try:
                    video_io.seek(0)
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=video_io,
                        caption=caption_msg,
                        reply_markup=split_kb,
                        read_timeout=180.0,
                        write_timeout=180.0
                    )
                    break
                except Exception as vid_err:
                    if attempt == 2:
                        raise vid_err
                    await asyncio.sleep(3)

            user_sessions.pop(user_id, None)
        except Exception as e:
            logger.error(f"Lỗi Phase 2: {e}", exc_info=True)
            fail_kb = [[InlineKeyboardButton("📥 Lấy Clip Vừa Render Xong", callback_data="btn_fetch_latest_video")]]
            await progress_msg.edit_text(
                f"❌ Quá trình gửi video gặp sự cố: `{str(e)}`\n\nNếu video đã render xong trong máy, bạn bấm nút bên dưới hoặc gõ lệnh `/layclip` để bot gửi lại ngay!",
                reply_markup=InlineKeyboardMarkup(fail_kb),
                parse_mode="Markdown"
            )

    # --- 3. VIET LAI KICH BAN ---
    elif action == "btn_rewrite":
        await query.message.reply_text("✍️ Đang viết lại kịch bản với phong cách mới...")
        try:
            new_caption = session["caption"] + " (hãy thử phong cách chuyển cảnh sáng tạo, động tác nhịp điệu nhanh, có tiếp đất ngoạn mục hơn)"
            result = await asyncio.to_thread(generate_script_and_prompt, session["image_bytes_list"], new_caption)
            duration = float(result.get("duration", 10.0))
            session["vietnamese_script"] = result["vietnamese_script"]
            session["qwen_prompts"] = result.get("qwen_prompts", [result.get("qwen_prompt")])
            session["minimax_prompt"] = result["minimax_prompt"]
            session["duration"] = duration
            num_storyboards = len(session["qwen_prompts"])

            btn_label = f"📸 1. Tạo {num_storyboards} Ảnh Storyboard Để Duyệt (Qwen)"
            keyboard = [
                [InlineKeyboardButton(btn_label, callback_data="btn_run_phase1_only")],
                [
                    InlineKeyboardButton(f"{'✅ ' if duration == 10 else ''}⏱ 10s", callback_data="btn_dur_10"),
                    InlineKeyboardButton(f"{'✅ ' if duration == 12 else ''}⏱ 12s", callback_data="btn_dur_12"),
                    InlineKeyboardButton(f"{'✅ ' if duration == 15 else ''}⏱ 15s", callback_data="btn_dur_15"),
                ],
                [InlineKeyboardButton("✍️ Viết Lại Lần Nữa", callback_data="btn_rewrite")],
                [InlineKeyboardButton("❌ Hủy", callback_data="btn_cancel")]
            ]
            await query.message.reply_text(
                f"🎬 **KỊCH BẢN MỚI ({num_storyboards} STORYBOARDS):**\n\n{result['vietnamese_script']}\n\n⏱ Thời lượng: {duration:.0f}s",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.message.reply_text(f"❌ Lỗi khi viết lại kịch bản: {str(e)}")

    # --- 4. HUY PHIEN ---
    elif action == "btn_cancel":
        user_sessions.pop(user_id, None)
        await query.edit_message_text("❌ Đã hủy phiên làm việc. Hãy gửi ảnh mới bất kỳ lúc nào bạn muốn!")

def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("❌ LỖI: Vui lòng điền TELEGRAM_BOT_TOKEN trong file .env trước khi chạy!")
        return

    # Tang Timeout HTTPX len 180s chong triet de loi TimedOut khi tai anh/video
    request_config = HTTPXRequest(
        connection_pool_size=16,
        read_timeout=180.0,
        write_timeout=180.0,
        connect_timeout=60.0,
        pool_timeout=60.0
    )

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(request_config).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("layclip", layclip_command))
    app.add_handler(CommandHandler("layvideo", layclip_command))
    app.add_handler(CommandHandler("getvideo", layclip_command))
    app.add_handler(CommandHandler("tachclip", tachclip_command))
    app.add_handler(CommandHandler("splitclip", tachclip_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    app.add_handler(CallbackQueryHandler(handle_button_callback))

    print("=" * 60)
    print("🚀 AUTOMATION MULTI-OUTFIT & 360° STORYBOARD (QWEN STILLS ➡️ MINIMAX H3)")
    print("✨ TỰ ĐỘNG KHÓA MẶT HOST CHÂU Á, TẠO ĐỦ MẶT TRƯỚC VÀ MẶT SAU TỪNG ÁO")
    print("🔄 HỖ TRỢ TẠO LẠI RIÊNG TỪNG ẢNH BẤT KỲ TRƯỚC KHI DUYỆT")
    print("📥 LỆNH /layclip ĐỂ TẢI VIDEO MỚI NHẤT VỀ TELEGRAM BẤT KỲ LÚC NÀO")
    print("🛡️ 16GB VRAM SAFETY: DUYỆT TOÀN BỘ ẢNH TRƯỚC KHI GEN VIDEO HÀNG LOẠT")
    print("=" * 60)
    app.run_polling()

if __name__ == "__main__":
    main()
