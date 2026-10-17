import os
import re
import json
import uuid
import tempfile
import subprocess
from pathlib import Path
from config import AGY_MODEL, GEMINI_API_KEY, GEMINI_MODEL, USE_ANTIGRAVITY_CLI

def ensure_all_views_prompts(prompts: list[str], num_images: int) -> list[str]:
    """Dam bao moi chiec ao luon co du 2 prompt: 1 Mat truoc (Front View) va 1 Mat sau (Back View)"""
    target_count = num_images * 2
    if len(prompts) == target_count:
        return prompts

    # Neu da co num_images prompts (1 prompt/ao)
    if len(prompts) == num_images:
        expanded = []
        for i, p in enumerate(prompts):
            p_front = p
            if "rear" in p_front.lower() or "back view" in p_front.lower() or "from behind" in p_front.lower():
                p_front = (
                    p_front.replace("rear three-quarter view", "front-view commercial photograph")
                           .replace("rear back-view", "front-view commercial photograph")
                           .replace("rear view", "front view")
                           .replace("back view", "front view")
                           .replace("seen from behind", "facing the camera")
                )
            if "front view" not in p_front.lower() and "front-view" not in p_front.lower():
                p_front += " Front-view commercial photograph facing the camera."

            p_back = p
            if "front view" in p_back.lower() or "front-view" in p_back.lower() or "facing the camera" in p_back.lower():
                p_back = (
                    p_back.replace("front-view commercial photograph", "rear three-quarter view commercial photograph")
                          .replace("front view", "rear back view")
                          .replace("front-view", "rear back-view")
                          .replace("facing the camera", "seen from behind")
                )
            if "rear" not in p_back.lower() and "back" not in p_back.lower():
                p_back += " Dynamic rear three-quarter view showing the back details of the clothing, athletic back muscles, and confident posture."

            expanded.append(p_front)
            expanded.append(p_back)
        return expanded

    # Neu chi co 1 prompt duy nhat hoac so luong khac
    base_p = prompts[0] if prompts else (
        "A vertical 9:16 full-body commercial photograph set in the scene environment. "
        "The subject is the handsome muscular athletic Asian host from <image1>, dressed in clothing from <image2>. "
        "Keep face and identity 100% identical to <image1>. CLEAN SKIN MANDATE: ZERO tattoos, NO body ink, NO hat. 8k photorealistic."
    )
    expanded = []
    for i in range(num_images):
        p_front = base_p.replace("<image2>", f"<image2> (Outfit {i+1})")
        if "rear" in p_front.lower() or "back view" in p_front.lower() or "from behind" in p_front.lower():
            p_front = p_front.replace("rear view", "front view").replace("back view", "front view").replace("seen from behind", "facing the camera")
        if "front view" not in p_front.lower():
            p_front += " Front-view commercial photograph facing the camera."

        p_back = base_p.replace("<image2>", f"<image2> (Outfit {i+1})")
        if "front view" in p_back.lower() or "facing the camera" in p_back.lower():
            p_back = p_back.replace("front view", "rear back view").replace("facing the camera", "seen from behind")
        if "rear" not in p_back.lower() and "back" not in p_back.lower():
            p_back += " Dynamic rear three-quarter view showing the back details of the clothing and athletic back posture."

        expanded.append(p_front)
        expanded.append(p_back)
    return expanded

def extract_json_from_text(text: str, user_caption: str = "", num_images: int = 1) -> dict:
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        json_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                data = None
        else:
            data = None

    if not data:
        data = {
            "vietnamese_script": (
                f"🎬 **KỊCH BẢN VIDEO THƯƠNG MẠI ({num_images} TRANG PHỤC - {num_images*2} GÓC NHÌN - 10 GIÂY)**\n\n"
                "• **BỐI CẢNH TỔNG THỂ:** Sân tập thể thao năng động, ánh sáng điện ảnh chuyên nghiệp.\n\n"
                "• **PHÂN ĐOẠN 1 [00:00 - 00:05] (5s):** Host xuất hiện trong Trang phục 1 (mặt trước & xoay người khoe chi tiết lưng áo).\n\n"
                "• **PHÂN ĐOẠN 2 [00:05 - 00:10] (5s):** Chuyển cảnh ngoạn mục (nhào lộn/tiếp đất), Host biến hình sang Trang phục 2 (mặt trước & mặt sau hoàn thiện hero finish).\n\n"
                "• **ĐỊNH DẠNG XUẤT:** 1 Video liền mạch 10s (có kèm nút [✂️ Tách Clip] để lấy 2 file rời 5s nếu muốn ghép CapCut)!"
            ),
            "qwen_prompts": [],
            "minimax_prompt": "",
            "duration": 10.0
        }

    # Uu tien thoi luong khach hang ghi trong caption (10s, 12s, 15s)
    caption_lower = user_caption.lower()
    dur_match = re.search(r"\b(\d{1,2})\s*(?:s|giay|giây|second|seconds)\b", caption_lower)
    if dur_match:
        explicit_dur = float(dur_match.group(1))
        if 5.0 <= explicit_dur <= 30.0:
            data["duration"] = explicit_dur
    else:
        if "duration" not in data or data["duration"] > 25.0:
            data["duration"] = 10.0
        else:
            data["duration"] = float(data["duration"])

    prompts = data.get("qwen_prompts", [])
    if isinstance(prompts, str):
        prompts = [prompts]
    elif not prompts and "qwen_prompt" in data:
        prompts = [data["qwen_prompt"]]

    # Luon dam bao co du num_images * 2 prompts (Moi ao deu co Front View va Back View)
    data["qwen_prompts"] = ensure_all_views_prompts(prompts, num_images)
    data["qwen_prompt"] = data["qwen_prompts"][0]

    # Dam bao minimax_prompt tham chieu dung so luong anh
    if num_images == 2:
        if "<Picture 3>" not in data.get("minimax_prompt", "") or "<Picture 4>" not in data.get("minimax_prompt", ""):
            data["minimax_prompt"] = (
                "r34l1sm\n\nsubject_definitions:\n"
                "<Subject 1> is the host: a handsome, muscular athletic Asian man from <Picture 1>, <Picture 2>, <Picture 3>, and <Picture 4>, preserving his exact facial features, short styled haircut, mustache and goatee, and athletic muscular physique with completely clean skin and ZERO tattoos. In Clip 1, he is wearing Outfit 1 from <Picture 1> (front) and <Picture 2> (back). In Clip 2, he is wearing Outfit 2 from <Picture 3> (front) and <Picture 4> (back).\n\n"
                "summary:\n[reference generation] Dynamic cinematic commercial showing <Subject 1> performing athletic movement with a seamless acrobatic costume transition.\n\n"
                "retention_analysis:\n<Subject 1>: fully_preserved.\n<Picture 1>: fully_preserved.\n<Picture 2>: fully_preserved.\n<Picture 3>: fully_preserved.\n<Picture 4>: fully_preserved.\n\n"
                "detailed_description:\n[Clip 1] From 00:00.000 to 00:05.000, dynamic camera tracking <Subject 1> wearing Outfit 1 (<Picture 1> front, <Picture 2> back) starting his athletic leap and rotational movement in the scene environment.\n"
                "[Clip 2] At 00:05.000 to 00:10.000, seamless transition on landing as <Subject 1> transforms into Outfit 2 (<Picture 4> back view showing back graphics and <Picture 3> front view as he turns to camera) with a confident heroic finish.\n\n"
                "overall_soundscape:\nCinematic atmospheric whoosh on transition with energetic electronic beat."
            )
    elif num_images == 1:
        if "<Picture 2>" not in data.get("minimax_prompt", ""):
            data["minimax_prompt"] = (
                "r34l1sm\n\nsubject_definitions:\n"
                "<Subject 1> is the host: a handsome, muscular athletic Asian man from <Picture 1> and <Picture 2>, preserving his exact facial features, short styled haircut, mustache and goatee, and athletic muscular physique with completely clean skin and ZERO tattoos. He is wearing the stylish outfit from <Picture 1> (front) and <Picture 2> (back) in the scene environment.\n\n"
                "summary:\n[reference generation] Dynamic cinematic commercial showing <Subject 1> moving with confidence in the stylish outfit.\n\n"
                "retention_analysis:\n<Subject 1>: fully_preserved.\n<Picture 1>: fully_preserved.\n<Picture 2>: fully_preserved.\n\n"
                "detailed_description:\n[Clip 1] From 00:00.000 to 00:05.000, tracking shot of <Subject 1> in <Picture 1> executing opening movement in the scene.\n"
                "[Clip 2] At 00:05.000 to 00:10.000, dynamic transition showing <Subject 1> in <Picture 2> revealing the back view of the clothing across his athletic body with confident hero finish.\n\n"
                "overall_soundscape:\nCinematic atmospheric breeze and upbeat electronic beat."
            )

    return data

def call_antigravity_cli(product_image_paths: list[str], user_caption: str) -> dict:
    num_images = len(product_image_paths)
    target_prompts = num_images * 2
    images_bullet = "\n".join([f"- Trang phuc {i+1} ({Path(p).name}): {Path(p).resolve()}" for i, p in enumerate(product_image_paths)])

    prompt = f"""
    Ban la mot dao dien sang tao quang cao video thuong mai thoi trang & the thao cao cap cho dinh dang doc 9:16 (TikTok, Reels, YouTube Shorts).
    Ban co kha nang thi giac phan tich anh san pham ti mi (mau sac, form dang silhouette, graphic truoc/sau, va phat hien anh ghep composite).

    DANH SACH FILE ANH SAN PHAM CAN XEM VA PHAN TICH ({num_images} ANH):
{images_bullet}

    HUONG DAN QUAN TRONG: Hay su dung cong cu view_file de xem tung file anh tren nham phan tich chinh xac mau sac (color), kieu dang form ao (silhouette), hinh in/graphic mat truoc va mat sau, va toa do crop (neu la anh composite).

    FLOW QUY TRINH BAT BUOC THEO YEU CAU KHACH HANG:
    1. PHAN TICH ANH SAN PHAM ({num_images} ANH):
       - Kiem tra tung anh xem co phai anh composite (anh ghep chua ca 2 nguoi mau mat truoc va mat sau trong 1 anh) hay khong.
       - Neu la anh composite (2 nguoi mau trong 1 anh):
         * Xac dinh toa do crop mat truoc 'front_crop': [ymin, xmin, ymax, xmax] (gia tri tu 0.0 den 1.0) chi chua phan ao/than nguoi mau mat truoc. QUAN TRONG: ymin >= 0.20 de loai bo hoan toan dau, mat va mu non cua nguoi mau goc; lay rong sang hai ben de giu du form ong tay ao boxy fit.
         * Xac dinh toa do crop mat sau 'back_crop': [ymin, xmin, ymax, xmax] chi chua phan ao/lung nguoi mau mat sau. ymin >= 0.20 de loai bo dau va mu non.
       - Mo ta chi tiet:
         * Form dang 'silhouette': vi du "stylish relaxed drop-shoulder streetwear gym t-shirt matching the exact proportions from <image2>"
         * Mau sac 'color': vi du "rich chocolate brown" hoac "matte washed black"
         * Graphic mat truoc 'front_graphic': vi du "small vibrant yellow cursive script Members Only on the left chest" hoac "minimalist crisp white uppercase block text OWN IT centered horizontally across the chest"
         * Graphic mat sau 'back_graphic': vi du "large graphic across the upper back reading RAW in bold block lettering overlaid by Members Only in vibrant yellow cursive script" hoac "large typography across the back reading WALK IN LIKE YOU OWN IT with diagonal slash line and 3 logo"

    2. BOI CANH VIDEO (LAY TRUC TIEP TU Y TUONG CUA KHACH HANG, TUYET DOI KHONG GAN BAY BA):
       - Y tuong khach hang: "{user_caption if user_caption else 'Tao video thoi trang the thao chuyen dong dep mat ton voc dang Host'}".
       - Neu y tuong calisthenics/the thao -> "modern outdoor calisthenics athletic workout park with matte-black training bars and shock-absorbing green turf under golden hour sunlight".
       - Neu y tuong gym -> "modern luxury fitness gym with dumbbells, power racks, and neon athletic lighting".
       - Neu y tuong streetwear/dao pho -> "modern urban city street with contemporary architecture and soft evening streetlights".

    3. QUY TAC TAO DUNG {target_prompts} PROMPTS CHO QWEN (MOI AO 2 ANH: TRUOC & SAU):
       - Prompt Mat truoc (Front View):
         "solo, 1man, single person only, exactly one person in the entire frame, no other people. A vertical 9:16 full-body commercial photograph set in [BOI CANH]. The subject is the handsome muscular athletic Asian host from <image1>, front view, standing facing directly forward towards the camera. Keep his exact face, facial features, dark eyes, masculine jawline, signature dark mustache and goatee beard, short styled haircut, and tan skin tone from <image1> 100% identical and unchanged. He has his distinct dark mustache and goatee beard. Dressed in the [color] [silhouette] from <image2>, faithfully featuring the exact [front_graphic] from <image2>, paired with dark athletic workout shorts. GARMENT SILHOUETTE MANDATE: Faithfully replicate the exact garment silhouette, cut, and proportions from <image2>: stylish relaxed drop-shoulder streetwear fit with clean structured drape, perfectly proportioned to match <image2> — neither tight nor excessively baggy. CLEAN BODY MANDATE: Completely clean bare arms and legs, smooth skin, ZERO tattoos, NO body ink, NO sleeve tattoos, NO hat, NO baseball cap. 8k resolution, cinematic lighting, photorealistic."
       - Prompt Mat sau (Back View - TUYET DOI KHONG NHAC DEN MAT/MUI/MIENG):
         "solo, 1man, single person only, exactly one person in the entire frame, no other people in background. A vertical 9:16 full-body commercial photograph set in [BOI CANH]. The subject is the handsome muscular athletic Asian host from <image1>, dynamic rear back view seen from behind, completely turned away from the camera. Showing the back of his head with his signature dark short haircut from <image1>, muscular neck, powerful upper back muscles, athletic V-taper, and broad shoulders turned away from camera. Completely bare head, NO hat, NO baseball cap, NO beanie. Dressed in the [color] [silhouette] from <image2>, faithfully reproducing the exact [back_graphic] from <image2>, paired with dark athletic workout shorts. GARMENT SILHOUETTE MANDATE: Faithfully replicate the exact garment silhouette, cut, and proportions from <image2>: stylish relaxed drop-shoulder streetwear fit with clean structured drape, perfectly proportioned to match <image2> — neither tight nor excessively baggy. CLEAN BODY MANDATE: Completely clean bare arms and legs, smooth skin, ZERO tattoos, NO body ink, NO sleeve tattoos. 8k resolution photorealistic."

    4. PROMPT VIDEO MINIMAX H3:
       - Chuan cu phap MiniMax H3: r34l1sm, subject_definitions...
       - Detailed description tung clip 5s voi cu transition bien hinh ngoan muc.

    TRA VE DUY NHAT 1 DOI TUONG JSON THUAN TUY:
    {{
        "products": [
            {{
                "is_composite": true,
                "front_crop": [0.45, 0.55, 0.95, 0.98],
                "back_crop": [0.15, 0.05, 0.85, 0.65],
                "color": "rich chocolate brown",
                "silhouette": "heavyweight oversized drop-shoulder boxy fit streetwear gym t-shirt",
                "front_graphic": "small vibrant yellow cursive script Members Only on left chest",
                "back_graphic": "large graphic across the upper back reading RAW in bold block lettering overlaid by Members Only in yellow cursive script"
            }}
        ],
        "vietnamese_script": "Kich ban phan canh chi tiet ro tung phan doan:\\n• PHAN DOAN 1 [00:00 - 00:05] (5s): Host mac Trang phuc 1 khoi dau hanh dong (truoc & sau)...\\n• PHAN DOAN 2 [00:05 - 00:10] (5s): Chuyen canh bien hinh sang Trang phuc 2...\\n• DINH DANG XUAT: 1 Video lien mach 10s (chuyen canh muot ma)",
        "duration": 10.0,
        "qwen_prompts": [
            "Prompt 1 (Ao 1 - Mat truoc)...",
            "Prompt 2 (Ao 1 - Mat sau)..."
        ],
        "minimax_prompt": "Prompt tieng Anh MiniMax H3..."
    }}
    """

    cmd = [
        "agy",
        "--dangerously-skip-permissions",
        "--model", AGY_MODEL,
        "-p", prompt
    ]

    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"Loi Antigravity CLI: {result.stderr or result.stdout}")

    return extract_json_from_text(result.stdout, user_caption=user_caption, num_images=num_images)

def generate_script_and_prompt(image_bytes_input, user_caption: str = "") -> dict:
    temp_dir = Path(tempfile.gettempdir()) / "marketing_ai"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(image_bytes_input, list):
        image_list = image_bytes_input
    else:
        image_list = [image_bytes_input]

    temp_paths = []
    for idx, img_b in enumerate(image_list):
        path = temp_dir / f"temp_input_product_{idx+1}.png"
        with open(path, "wb") as f:
            f.write(img_b)
        temp_paths.append(str(path))

    return call_antigravity_cli(temp_paths, user_caption)
