import os
import re
import json
import uuid
import time
import random
import requests
import websocket
from pathlib import Path
from config import (
    COMFYUI_URL,
    COMFYUI_WS_URL,
    COMFYUI_INPUT_DIR,
    COMFYUI_OUTPUT_DIR,
    WORKFLOW_TEMPLATE_PATH,
    HOST_IMAGE_NAME
)

_CACHED_AVAILABLE_MODELS = None

def get_available_comfy_models() -> dict:
    """Quet cac model thuc te co trong ComfyUI cua may nguoi dung (co cache)"""
    global _CACHED_AVAILABLE_MODELS
    if _CACHED_AVAILABLE_MODELS is not None:
        return _CACHED_AVAILABLE_MODELS
    try:
        r = requests.get(f"{COMFYUI_URL}/object_info", timeout=15)
        info = r.json()
        _CACHED_AVAILABLE_MODELS = {
            "clip": info.get("CLIPLoader", {}).get("input", {}).get("required", {}).get("clip_name", [[]])[0],
            "vae": info.get("VAELoader", {}).get("input", {}).get("required", {}).get("vae_name", [[]])[0],
            "unet": info.get("UNETLoader", {}).get("input", {}).get("required", {}).get("unet_name", [[]])[0],
        }
        return _CACHED_AVAILABLE_MODELS
    except Exception as e:
        print(f"[Warning] Khong the lay object_info tu ComfyUI: {e}")
        return {"clip": [], "vae": [], "unet": []}

def upload_image(image_bytes: bytes, filename: str = "product_input.png") -> str:
    """Upload anh nhan tu Telegram vao thu muc input cua ComfyUI"""
    files = {"image": (filename, image_bytes, "image/png")}
    data = {"overwrite": "true"}
    resp = requests.post(f"{COMFYUI_URL}/upload/image", files=files, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    return result["name"]

# ==========================================
# PHASE 1: CHI CHAY GROUP 1 (QWEN - TAO ANH 9:16)
# KHOA CHAT BAN SAC HOST CO DINH (<image1>), LOAI BO HINH XAM & NON MU
# DINH DANG DOC 9:16 (1088x1920) SAC NET CHO REELS / TIKTOK
# ==========================================
def build_qwen_image_prompt(raw_ui: dict, product_image_name: str, prompt_text: str, seed: int = None) -> dict:
    links_map = {}
    for link in raw_ui.get("links", []):
        if len(link) >= 3:
            links_map[link[0]] = [str(link[1]), link[2]]

    raw_node_ids = {str(n["id"]) for n in raw_ui.get("nodes", [])}
    is_new_qwen = "226" in raw_node_ids or "216" in raw_node_ids or "202" in raw_node_ids

    if is_new_qwen:
        qwen_node_ids = {
            "201", "202", "204", "205", "206", "207", "208", 
            "209", "212", "213", "214", "216", "217", "218", 
            "219", "220", "221", "222", "226"
        }
    else:
        qwen_node_ids = {
            "30001", "30002", "30003", "30004", "30005", "30006", 
            "30008", "30009", "30010", "30011", "30012", "30018", 
            "30019", "30024", "30100"
        }

    chosen_seed = seed if seed is not None else random.randint(1, 10**14)

    is_back_view = any(w in prompt_text.lower() for w in ["rear", "back view", "seen from behind", "from behind", "back of", "turn away", "turned away"])

    # Mandates quan trong de khoa chat form oversize, boi canh tu nhien, va bo brick wall
    bg_mandate = "BACKGROUND MANDATE: Completely replace and discard the entire background from BOTH <image1> and <image2>. ZERO brick walls, NO red bricks, NO brick texture, NO indoor walls. The subject is situated 100% outdoors in the specified scene environment."
    fit_mandate = "GARMENT SILHOUETTE MANDATE: Faithfully replicate the exact garment silhouette, cut, sleeve length, and proportions seen in <image2>: a stylish relaxed drop-shoulder streetwear fit with clean structured drape. Perfectly proportioned to match <image2> — neither tight nor excessively baggy."
    graphic_mandate = "GRAPHIC TRANSFER MANDATE: Directly replicate the exact graphic artwork, typography layout, and logo from <image2> onto the shirt with 100% precision. Replicate the visual print layout from <image2>."
    clean_skin_mandate = "CLEAN SKIN MANDATE: Completely clean bare arms and legs, smooth clean skin, ZERO tattoos, NO body ink, NO sleeve tattoos, NO hat, NO baseball cap. Do NOT copy any tattoos, headwear, or skin markings from <image2>."

    clean_p = prompt_text.strip()
    if is_back_view:
        for word in ["keep the exact face", "facial features", "eyes", "nose", "mouth", "facial identity", "facing the camera", "front view", "mustache", "goatee"]:
            clean_p = re.sub(rf"\b{re.escape(word)}\b", "", clean_p, flags=re.IGNORECASE)
        back_identity = "The subject is the handsome muscular athletic Asian host from <image1>, seen from behind in a dynamic rear back view completely turned away from the camera on the turf, showing his signature dark short haircut, muscular neck, and broad athletic upper back posture. Bare head, NO hat, NO baseball cap. "
        final_prompt_text = f"solo, 1man, single person only, exactly one person in the entire frame, no other people in background. {clean_p}. {back_identity} {fit_mandate} {graphic_mandate} {bg_mandate} {clean_skin_mandate} Dynamic cinematic lighting, shallow depth of field, 8k resolution, photorealistic."
    else:
        host_face_identity = "The subject is the handsome muscular athletic Asian host from <image1>, front view, standing facing directly forward towards the camera on the turf. Keep his exact face, facial features, dark eyes, masculine jawline, signature dark mustache and goatee beard, short styled haircut, and tan skin tone from <image1> 100% identical and unchanged. He has his distinct dark mustache and goatee beard. "
        final_prompt_text = f"solo, 1man, single person only, exactly one person in the entire frame, no other people in background. {clean_p}. {host_face_identity} {fit_mandate} {graphic_mandate} {bg_mandate} {clean_skin_mandate} Dynamic cinematic lighting, shallow depth of field, 8k resolution, photorealistic."

    prompt_g1 = {}
    for n in raw_ui["nodes"]:
        nid = str(n["id"])
        if nid not in qwen_node_ids:
            continue

        ntype = n["type"]
        inputs = {}

        if "widgets_values_named" in n and isinstance(n["widgets_values_named"], dict):
            for k, v in n["widgets_values_named"].items():
                inputs[k] = v
        elif "widgets_values" in n and isinstance(n["widgets_values"], dict):
            for k, v in n["widgets_values"].items():
                inputs[k] = v

        for inp in n.get("inputs", []):
            name = inp.get("name")
            lid = inp.get("link")
            if lid in links_map:
                origin_id, origin_slot = links_map[lid]
                if origin_id in qwen_node_ids:
                    inputs[name] = [origin_id, origin_slot]

        # --- CAU HINH QUY TRINH MOI (CO LORA LENOVO QWEN 2.1) ---
        if is_new_qwen:
            if nid == "205":
                inputs["image"] = HOST_IMAGE_NAME # <image1>: Anh Host co dinh
            elif nid == "207":
                inputs["image"] = product_image_name # <image2>: Anh trang phuc tu Telegram
            elif nid == "226": # LoRA Lenovo Qwen 2.1 (Dat 0.0 o base pass, kich hoat 0.65 o refiner pass)
                inputs["lora_name"] = "lenovo_qwen21.safetensors"
                inputs["strength_model"] = 0.0
                inputs["strength_clip"] = 0.0
            elif nid == "208": # LoRA Fedor Bypass (Dat 0.0 o base pass de giu attention vao visual reference chuan)
                inputs["lora_name"] = "fedor_bypass.safetensors"
                inputs["strength_model"] = 0.0
                inputs["strength_clip"] = 0.0
            elif nid == "212": # QwenImage21Cache (QUAN TRONG: TAT CACHE DE KHONG DE LATENT RUN CU BLEED QUA RUN MOI)
                inputs["device"] = "off"
                inputs["dtype"] = "default"
            elif nid == "209": # PixaromaSizes 9:16 (Chuan 1088x1920 cho do phan giai cao, graphic sac net)
                inputs["SizesState"] = json.dumps({
                    "version": 1,
                    "sizes": [[1088, 1920]],
                    "selected": 0,
                    "orientation": "portrait",
                    "snap": 32,
                    "w": 1088,
                    "h": 1920
                })
            elif nid == "218": # EmptyLatentImage (1088x1920 9:16)
                inputs["width"] = 1088
                inputs["height"] = 1920
            elif nid == "213": # PixaromaPrompt
                inputs["PromptState"] = json.dumps({"text": final_prompt_text, "order": "mine", "sep": ", "})
            elif nid == "214": # PixaromaSeed
                inputs["SeedState"] = json.dumps({"seed": chosen_seed, "mode": "random", "compact": True, "digits": 16})
                inputs["seed"] = chosen_seed
            elif nid == "216": # TextEncodeQwenImage21
                # QUAN TRONG: Luon ket noi ca Host (<image1>), Trang phuc (<image2>) va VAE de encode reference
                inputs["images.image_1"] = ["205", 0] # Host character tu Node 205
                inputs["images.image_2"] = ["207", 0] # Trang phuc crop tu Node 207
                inputs["vae"] = ["206", 0] # Ket noi VAELoader tu Node 206

                base_neg = (
                    "brick wall, red bricks, brick texture, brick background, bricks, building wall, stone wall, indoor wall, studio backdrop, "
                    "tight t-shirt, slim fit, tight shirt, tight sleeves, fitted shirt, compression shirt, athletic undershirt, bodycon, "
                    "excessively baggy, tent shirt, poncho, oversized dress, oversized clown clothes, gigantic clothes, "
                    "2men, two men, two people, multiple people, group, crowd, background people, background person, extra person, clone, duplicate, side-by-side, split image, collage, "
                    "clean shaven, smooth chin, missing mustache, missing goatee, "
                    "hat, baseball cap, cap, beanie, headwear, "
                    "tattoos, tattoo, tattooed skin, body ink, arm tattoo, sleeve tattoo, wrist tattoo, neck tattoo, hand tattoo, ink, markings, "
                    "plain white background, solid white backdrop, plain studio background, cutout background, solid backdrop, "
                    "deformed hands, distorted limbs, extra fingers, blurry, low resolution, noise, amateur"
                )
                if is_back_view:
                    base_neg = "face, front view, facing camera, eyes, mouth, nose, facial features, " + base_neg

                inputs["negative_prompt"] = base_neg
                inputs["resolution"] = 1024
                inputs.pop("images.image_3", None)
                inputs.pop("images.image_4", None)
            elif nid == "217": # KSampler (Euler + Simple scheduler, CFG 1.8, 25 steps cho visual transfer chuan 100%)
                inputs["cfg"] = 1.8
                inputs["steps"] = 25
                inputs["sampler_name"] = "euler"
                inputs["scheduler"] = "simple"
            elif nid == "221": # PixaromaPreview (Luu anh ket qua)
                inputs["filename_prefix"] = "QwenShots/multishot_9_16"
                inputs["save_mode"] = "save"

        # --- CAU HINH QUY TRINH CU (BACKWARD COMPATIBILITY) ---
        else:
            if ntype == "PixaromaSizes":
                inputs["SizesState"] = json.dumps({
                    "version": 1,
                    "sizes": [[1088, 1920]],
                    "selected": 0,
                    "orientation": "portrait",
                    "snap": 32,
                    "w": 1088,
                    "h": 1920
                })
            elif nid == "30019": # EmptyLatentImage
                inputs["width"] = 1088
                inputs["height"] = 1920
            elif ntype == "PixaromaPrompt":
                inputs["PromptState"] = json.dumps({"text": final_prompt_text, "order": "mine", "sep": ", "})
            elif ntype == "PixaromaSeed":
                inputs["SeedState"] = json.dumps({"seed": chosen_seed, "mode": "random", "compact": True, "digits": 16})
            elif nid == "30010":
                inputs["negative_prompt"] = (
                    "tattoos, tattoo, tattooed skin, body ink, arm tattoo, sleeve tattoo, wrist tattoo, neck tattoo, hand tattoo, ink, markings, "
                    "hat, baseball cap, beanie, headwear, "
                    "plain white background, solid white backdrop, plain studio background, cutout background, solid backdrop, "
                    "deformed hands, distorted limbs, extra fingers, blurry, low resolution, noise, amateur"
                )
                inputs["resolution"] = 1024
            elif nid == "30011":
                inputs["cfg"] = 3.0
                inputs["sampler_name"] = "res_2s"
                inputs["scheduler"] = "beta"
            elif nid == "30005":
                inputs["image"] = HOST_IMAGE_NAME
            elif nid == "30006":
                inputs["image"] = product_image_name
            elif nid == "30001":
                inputs["unet_name"] = "qwen_image_2.1_int8_convrot.safetensors"
            elif nid == "30002":
                inputs["clip_name"] = "qwen3vl_8b_int8_convrot.safetensors"
            elif nid == "30003":
                inputs["vae_name"] = "qwen_image_2.1_vae_bf16.safetensors"
            elif nid == "30100":
                inputs["filename_prefix"] = "QwenShots/multishot_9_16"

        prompt_g1[nid] = {
            "class_type": ntype,
            "inputs": inputs
        }

    return prompt_g1

# ==========================================
# PHASE 2: CHI CHAY GROUP 2 (MINIMAX H3 VIDEO 9:16)
# BYPASS 100% GROUP 1 DE GIAI PHONG VRAM
# NAP MULTI-REFERENCE TONG HOP CHO CAC CLIP THEO KICH BAN
# ==========================================
def build_minimax_video_prompt(raw_ui: dict, still_image_names: list[str] | str, prompt_text: str, duration: float = 10.0, video_quality: str = "720p") -> dict:
    if isinstance(still_image_names, str):
        still_image_names = [still_image_names]

    available_models = get_available_comfy_models()

    links_map = {}
    for link in raw_ui.get("links", []):
        if len(link) >= 3:
            links_map[link[0]] = [str(link[1]), link[2]]

    # Xu ly SetNode & GetNode
    set_nodes = {}
    for node in raw_ui.get("nodes", []):
        if node.get("type") == "SetNode":
            var_name = node.get("widgets_values_named", {}).get("Constant") or (node.get("widgets_values", [])[0] if node.get("widgets_values") else None)
            for inp in node.get("inputs", []):
                link_id = inp.get("link")
                if link_id is not None and link_id in links_map:
                    set_nodes[var_name] = links_map[link_id]
                    break

    get_nodes_resolved = {}
    for node in raw_ui.get("nodes", []):
        if node.get("type") == "GetNode":
            var_name = node.get("widgets_values_named", {}).get("Constant") or (node.get("widgets_values", [])[0] if node.get("widgets_values") else None)
            if var_name in set_nodes:
                get_nodes_resolved[str(node["id"])] = set_nodes[var_name]

    # Loai bo sach Group 1 (cac node Qwen moi 201-227 hoac node 30xxx cu) + cac node dummy/preview
    all_qwen_node_ids = {
        "201", "202", "204", "205", "206", "207", "208", "209", "210", 
        "211", "212", "213", "214", "216", "217", "218", "219", "220", 
        "221", "222", "224", "226", "227"
    }
    qwen_node_prefixes = "30"
    dummy_nodes = {"148", "149", "155", "159", "161", "162", "170", "171", "172", "173", "175", "176", "177", "178", "135", "9000"}

    prompt_g2 = {}
    for node in raw_ui.get("nodes", []):
        node_id = str(node["id"])
        node_type = node.get("type")

        # Bypass toan bo Group 1 va node khong can thiet
        if node_id in all_qwen_node_ids or node_id.startswith(qwen_node_prefixes) or node_id in dummy_nodes or node_type in ["MarkdownNote", "Note", "SetNode", "GetNode", "Fast Groups Bypasser (rgthree)"]:
            continue

        inputs = {}
        if "widgets_values_named" in node and isinstance(node["widgets_values_named"], dict):
            for k, v in node["widgets_values_named"].items():
                inputs[k] = v
        elif "widgets_values" in node and isinstance(node["widgets_values"], dict):
            for k, v in node["widgets_values"].items():
                inputs[k] = v

        for inp in node.get("inputs", []):
            name = inp.get("name")
            link_id = inp.get("link")
            if link_id is not None and link_id in links_map:
                origin_id, origin_slot = links_map[link_id]
                if origin_id in get_nodes_resolved:
                    resolved_id, resolved_slot = get_nodes_resolved[origin_id]
                    if resolved_id in dummy_nodes or resolved_id in all_qwen_node_ids or resolved_id.startswith(qwen_node_prefixes):
                        continue
                    inputs[name] = [resolved_id, resolved_slot]
                else:
                    if origin_id in dummy_nodes or origin_id in all_qwen_node_ids or origin_id.startswith(qwen_node_prefixes):
                        continue
                    inputs[name] = [origin_id, origin_slot]

        # Nap anh tinh dau tien vao Node 169
        if node_id == "169":
            inputs["image"] = still_image_names[0]
        elif node_id == "84": # Prompt
            inputs["value"] = prompt_text
        elif node_id == "74": # Thoi luong linh hoat (10.0 - 25.0 giay)
            inputs["value"] = float(duration)
        elif node_id == "200": # Chon dung ti le 9:16 va do phan giai 720p / 1080p an toan VRAM
            inputs["aspect_ratio"] = "9:16 (Portrait Widescreen)"
            inputs["multiple"] = 32
            # 720p: megapixels = 0.85 -> 736x1312 (chuan doc 720p 9:16, nhe va khong bao gio tran 16GB VRAM)
            # 1080p: megapixels = 1.0 -> 768x1376
            inputs["megapixels"] = 0.85 if video_quality == "720p" else 1.0

        elif node_type == "CLIPLoader":
            curr_clip = inputs.get("clip_name", "")
            if curr_clip not in available_models["clip"] and available_models["clip"]:
                selected_clip = available_models["clip"][0]
                for c in available_models["clip"]:
                    if "nvfp4" in c or "8b" in c:
                        selected_clip = c
                        break
                inputs["clip_name"] = selected_clip

        elif node_type == "VAELoader":
            curr_vae = inputs.get("vae_name", "")
            if "minimax_h3_video_vae_fp16.safetensors" in curr_vae:
                inputs["vae_name"] = "minimax_h3_video_vae_fp16.safetensors"

        prompt_g2[node_id] = {
            "class_type": node_type,
            "inputs": inputs
        }

    # Cau hinh Multi-Reference Images cho Node 56 MiniMax
    if "56" in prompt_g2:
        prompt_g2["56"]["inputs"]["ref_images.ref_image_0"] = ["169", 0]
        prompt_g2["56"]["inputs"]["ref_image_size"] = "match" # Khop kich thuoc video, giam tai VRAM va tang toc render
        
        # Neu co tu 2 anh tro len (chuyen canh / nhieu goc nhin), tao them cac LoadImage node bo sung
        for idx in range(1, len(still_image_names)):
            extra_node_id = f"2016{idx+1}"
            prompt_g2[extra_node_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": still_image_names[idx]}
            }
            prompt_g2["56"]["inputs"][f"ref_images.ref_image_{idx}"] = [extra_node_id, 0]

        # Xoa cac link ref_image thua
        for k in list(prompt_g2["56"]["inputs"].keys()):
            if k.startswith("ref_images.ref_image_"):
                slot_idx = int(k.replace("ref_images.ref_image_", ""))
                if slot_idx >= len(still_image_names):
                    del prompt_g2["56"]["inputs"][k]

    return prompt_g2

def execute_phase1_qwen(raw_ui: dict, product_image_name: str, qwen_prompt: str, client_id: str, seed: int = None, status_callback=None) -> tuple[bytes, str]:
    ws = websocket.WebSocket()
    ws.connect(f"{COMFYUI_WS_URL}?clientId={client_id}", timeout=15)

    api_prompt = build_qwen_image_prompt(raw_ui, product_image_name, qwen_prompt, seed=seed)
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": api_prompt, "client_id": client_id}, timeout=30)
    
    if resp.status_code != 200:
        ws.close()
        raise RuntimeError(f"ComfyUI Phase 1 Error ({resp.status_code}): {resp.text}")

    prompt_id = resp.json()["prompt_id"]
    saved_filename = None
    subfolder = "QwenShots"
    folder_type = "output"

    if status_callback:
        status_callback("📸 [Phase 1: Tạo ảnh 9:16] Đang render ảnh dọc sắc nét 1088x1920 (loại bỏ hình xăm)...")

    try:
        while True:
            raw_msg = ws.recv()
            if not isinstance(raw_msg, str):
                continue
            msg = json.loads(raw_msg)
            mtype = msg.get("type")
            data = msg.get("data", {})

            if mtype == "progress" and status_callback:
                cur = data.get("value", 0)
                total = data.get("max", 25)
                status_callback(f"📸 [Phase 1: Tạo ảnh 9:16] Qwen đang vẽ: {cur}/{total} bước...")

            elif mtype == "executing" and data.get("prompt_id") == prompt_id:
                node = data.get("node")
                if node is None:
                    break

            elif mtype == "executed" and data.get("prompt_id") == prompt_id:
                if str(data.get("node")) in ["221", "30100"]:
                    images = data.get("output", {}).get("images", [])
                    if images:
                        saved_filename = images[0].get("filename")
                        subfolder = images[0].get("subfolder", "QwenShots")
                        folder_type = images[0].get("type", "output")

            elif mtype == "execution_error":
                raise RuntimeError(f"Phase 1 Execution Error: {data.get('exception_message')}")
    finally:
        ws.close()

    if not saved_filename:
        try:
            h_resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
            if h_resp.status_code == 200:
                h_data = h_resp.json().get(prompt_id, {})
                for out_nid in ["221", "30100"]:
                    outputs = h_data.get("outputs", {}).get(out_nid, {}).get("images", [])
                    if outputs:
                        saved_filename = outputs[0].get("filename")
                        subfolder = outputs[0].get("subfolder", "QwenShots")
                        folder_type = outputs[0].get("type", "output")
                        break
        except Exception as e:
            print(f"[Warning] Loi khi lay history: {e}")

    if not saved_filename:
        raise FileNotFoundError("Không nhận được ảnh kết quả từ Qwen (Phase 1).")

    view_resp = requests.get(f"{COMFYUI_URL}/view", params={"filename": saved_filename, "subfolder": subfolder, "type": folder_type}, timeout=60)
    view_resp.raise_for_status()
    img_bytes = view_resp.content

    # Cắt chuẩn chính xác 1080x1920 (chuẩn tỉ lệ 9:16 sắc nét tuyệt đối, không biến dạng)
    try:
        from PIL import Image
        import io
        pil_im = Image.open(io.BytesIO(img_bytes))
        w, h = pil_im.size
        if w == 1088 and h == 1920:
            pil_im = pil_im.crop((4, 0, 1084, 1920)) # Chính xác 1080x1920
            out_buf = io.BytesIO()
            pil_im.save(out_buf, format="PNG")
            img_bytes = out_buf.getvalue()
        elif w != 1080 or h != 1920:
            pil_im = pil_im.resize((1080, 1920), Image.Resampling.LANCZOS)
            out_buf = io.BytesIO()
            pil_im.save(out_buf, format="PNG")
            img_bytes = out_buf.getvalue()
    except Exception as crop_err:
        print(f"[Warning] Loi khi cat 1080x1920: {crop_err}")

    target_input_name = f"host_wearing_product_{uuid.uuid4().hex[:6]}.png"
    target_path = COMFYUI_INPUT_DIR / target_input_name
    try:
        with open(target_path, "wb") as f:
            f.write(img_bytes)
    except Exception as e:
        print(f"[Warning] Khong the ghi truc tiep vao input dir: {e}")
        upload_image(img_bytes, target_input_name)

    return img_bytes, target_input_name

def execute_phase2_minimax(raw_ui: dict, still_image_names: list[str] | str, video_prompt: str, duration: float, client_id: str, video_quality: str = "720p", status_callback=None) -> bytes:
    ws = websocket.WebSocket()
    ws.connect(f"{COMFYUI_WS_URL}?clientId={client_id}", timeout=15)

    api_prompt = build_minimax_video_prompt(raw_ui, still_image_names, video_prompt, duration, video_quality=video_quality)
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": api_prompt, "client_id": client_id}, timeout=30)
    
    if resp.status_code != 200:
        ws.close()
        raise RuntimeError(f"ComfyUI Phase 2 Error ({resp.status_code}): {resp.text}")

    prompt_id = resp.json()["prompt_id"]
    video_filename = None
    subfolder = ""
    folder_type = "output"

    if status_callback:
        status_callback(f"🚀 [Phase 2: Render Video 9:16] Đã giải phóng Qwen! Đang render video MiniMax {duration:.0f}s...")

    try:
        while True:
            raw_msg = ws.recv()
            if not isinstance(raw_msg, str):
                continue
            msg = json.loads(raw_msg)
            mtype = msg.get("type")
            data = msg.get("data", {})

            if mtype == "progress" and status_callback:
                cur = data.get("value", 0)
                total = data.get("max", 100)
                status_callback(f"🚀 [Phase 2: Render Video 9:16] MiniMax đang render: {cur}/{total} bước ({int(cur/total*100)}%)...")

            elif mtype == "executing" and data.get("prompt_id") == prompt_id:
                node = data.get("node")
                if node is None:
                    break
                elif status_callback:
                    status_callback(f"⚙️ Đang xử lý Node [{node}]...")

            elif mtype == "executed" and data.get("prompt_id") == prompt_id:
                if str(data.get("node")) == "141":
                    node_out = data.get("output", {})
                    # Chu y: VHS_VideoCombine su dung 'gifs', cac node khac co the su dung 'videos' hoac 'filenames'
                    items = node_out.get("gifs", []) or node_out.get("videos", []) or node_out.get("filenames", [])
                    if items:
                        first_item = items[0]
                        if isinstance(first_item, dict):
                            video_filename = first_item.get("filename")
                            subfolder = first_item.get("subfolder", "")
                            folder_type = first_item.get("type", "output")
                        elif isinstance(first_item, str):
                            video_filename = Path(first_item).name

            elif mtype == "execution_error":
                raise RuntimeError(f"Phase 2 Execution Error: {data.get('exception_message')}")
    finally:
        ws.close()

    # 1. Fallback tim qua history neu websocket bi lo hoac khong bat duoc
    if not video_filename:
        try:
            h_resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
            if h_resp.status_code == 200:
                h_data = h_resp.json().get(prompt_id, {})
                for nid, nout in h_data.get("outputs", {}).items():
                    items = nout.get("gifs", []) or nout.get("videos", []) or nout.get("filenames", [])
                    if items:
                        first_item = items[0]
                        if isinstance(first_item, dict):
                            video_filename = first_item.get("filename")
                            subfolder = first_item.get("subfolder", "")
                            folder_type = first_item.get("type", "output")
                            break
                        elif isinstance(first_item, str):
                            video_filename = Path(first_item).name
                            break
        except Exception as e:
            print(f"[Warning] Loi khi lay video history: {e}")

    # 2. Doc truc tiep tu o dia neu file da ton tai (khong ton do tre HTTP)
    if video_filename:
        local_path = COMFYUI_OUTPUT_DIR / (subfolder or "") / video_filename
        if local_path.is_file():
            with open(local_path, "rb") as f:
                return f.read()

    # 3. Fallback quet truc tiep file .mp4 moi nhat trong COMFYUI_OUTPUT_DIR
    recent_mp4 = sorted(
        COMFYUI_OUTPUT_DIR.glob("*.mp4"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if recent_mp4:
        newest = recent_mp4[0]
        # Neu file duoc tao trong vong 60 phut gan nhat
        if (time.time() - newest.stat().st_mtime) < 3600:
            with open(newest, "rb") as f:
                return f.read()

    # 4. Fallback qua API /view neu van chua doc duoc
    if video_filename:
        view_resp = requests.get(f"{COMFYUI_URL}/view", params={"filename": video_filename, "subfolder": subfolder, "type": folder_type}, timeout=180)
        view_resp.raise_for_status()
        return view_resp.content

    raise FileNotFoundError("Không nhận được file video từ MiniMax (Phase 2).")

# ==========================================
# PHASE 1.5: REFINER PASS VOI LORA LENOVO & UPSCALE 1088x1920
# Gan LoRA Lenovo SAU KHI da co anh de tang do chan thuc, khu AI look
# Denoise thap (0.28) giu nguyen 100% graphic, mau ao, form ao va khuon mat
# ==========================================
def build_refiner_upscale_prompt(image_name: str, prompt_text: str = "", seed: int = None, lora_strength: float = 0.65, denoise: float = 0.28) -> dict:
    chosen_seed = seed if seed is not None else random.randint(1, 10**14)
    p_text = prompt_text or (
        "ultra-photorealistic raw commercial photography, shot on 35mm film, sharp focus, "
        "authentic natural human skin texture, fine skin pores, subsurface scattering, realistic lighting, "
        "highly detailed fabric weave of the cotton t-shirt, natural shadows, depth of field, 8k resolution, authentic photograph."
    )
    neg_prompt = (
        "cgi, 3d render, illustration, cartoon, anime, airbrushed, plastic skin, smooth waxy skin, doll-like, fake, "
        "blurry, distorted, low resolution, hat, baseball cap, tattoos, extra limbs"
    )

    api_prompt = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                "weight_dtype": "default"
            }
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                "type": "qwen_image",
                "device": "default"
            }
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "qwen_image_2.1_vae_bf16.safetensors"
            }
        },
        "4": { # LoRA Lenovo tang chan thuc
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "lenovo_qwen21.safetensors",
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": ["1", 0],
                "clip": ["2", 0]
            }
        },
        "5": { # LoRA Fedor Bypass
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "fedor_bypass.safetensors",
                "strength_model": 1.0,
                "strength_clip": 1.0,
                "model": ["4", 0],
                "clip": ["4", 1]
            }
        },
        "6": {
            "class_type": "QwenImage21Cache",
            "inputs": {
                "device": "off",
                "dtype": "default",
                "model": ["5", 0]
            }
        },
        "7": {
            "class_type": "ModelAttentionBackend",
            "inputs": {
                "attention": "comfy kitchen attention",
                "model": ["6", 0]
            }
        },
        "8": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_name
            }
        },
        "9": { # Upscale len 1088x1920 bang Lanczos
            "class_type": "ImageScale",
            "inputs": {
                "image": ["8", 0],
                "upscale_method": "lanczos",
                "width": 1088,
                "height": 1920,
                "crop": "disabled"
            }
        },
        "10": { # VAE Encode sang Latent
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["9", 0],
                "vae": ["3", 0]
            }
        },
        "11": { # Text Encode voi prompt tang chan thuc
            "class_type": "TextEncodeQwenImage21",
            "inputs": {
                "prompt": p_text,
                "negative_prompt": neg_prompt,
                "resolution": 1024,
                "clip": ["5", 1]
            }
        },
        "12": { # Refiner KSampler (denoise thap 0.28 giu nguyen 100% bo cuc & text)
            "class_type": "KSampler",
            "inputs": {
                "seed": chosen_seed,
                "steps": 20,
                "cfg": 2.5,
                "sampler_name": "res_2s",
                "scheduler": "beta",
                "denoise": denoise,
                "model": ["7", 0],
                "positive": ["11", 0],
                "negative": ["11", 1],
                "latent_image": ["10", 0]
            }
        },
        "13": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["12", 0],
                "vae": ["3", 0]
            }
        },
        "14": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "QwenShots/refined_1080p",
                "images": ["13", 0]
            }
        }
    }
    return api_prompt

def execute_refiner_qwen(image_name: str, client_id: str, prompt_text: str = "", seed: int = None, lora_strength: float = 0.65, denoise: float = 0.28, status_callback=None) -> tuple[bytes, str]:
    ws = websocket.WebSocket()
    ws.connect(f"{COMFYUI_WS_URL}?clientId={client_id}", timeout=15)

    api_prompt = build_refiner_upscale_prompt(image_name, prompt_text, seed, lora_strength, denoise)
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": api_prompt, "client_id": client_id}, timeout=30)
    if resp.status_code != 200:
        ws.close()
        raise RuntimeError(f"ComfyUI Refiner Error: {resp.text}")

    prompt_id = resp.json()["prompt_id"]
    saved_filename = None
    subfolder = "QwenShots"
    folder_type = "output"

    if status_callback:
        status_callback("✨ [LoRA Lenovo Refiner] Đang nâng cấp chân thực 1088x1920 (khử AI look, phủ vân da & vải thật)...")

    try:
        while True:
            raw_msg = ws.recv()
            if not isinstance(raw_msg, str):
                continue
            msg = json.loads(raw_msg)
            mtype = msg.get("type")
            data = msg.get("data", {})

            if mtype == "progress" and status_callback:
                cur = data.get("value", 0)
                total = data.get("max", 20)
                status_callback(f"✨ [Refiner Pass] Đang phủ vân da & ánh sáng điện ảnh: {cur}/{total} bước...")

            elif mtype == "executing" and data.get("prompt_id") == prompt_id:
                if data.get("node") is None:
                    break

            elif mtype == "executed" and data.get("prompt_id") == prompt_id:
                if str(data.get("node")) == "14":
                    images = data.get("output", {}).get("images", [])
                    if images:
                        saved_filename = images[0].get("filename")
                        subfolder = images[0].get("subfolder", "QwenShots")
                        folder_type = images[0].get("type", "output")
    finally:
        ws.close()

    if not saved_filename:
        h_resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        if h_resp.status_code == 200:
            h_data = h_resp.json().get(prompt_id, {})
            outputs = h_data.get("outputs", {}).get("14", {}).get("images", [])
            if outputs:
                saved_filename = outputs[0].get("filename")
                subfolder = outputs[0].get("subfolder", "QwenShots")
                folder_type = outputs[0].get("type", "output")

    if not saved_filename:
        raise FileNotFoundError("Không nhận được ảnh kết quả từ Refiner Pass.")

    view_resp = requests.get(f"{COMFYUI_URL}/view", params={"filename": saved_filename, "subfolder": subfolder, "type": folder_type}, timeout=60)
    view_resp.raise_for_status()
    return view_resp.content, saved_filename

