import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

# Cấu hình Antigravity Engine
USE_ANTIGRAVITY_CLI = os.getenv("USE_ANTIGRAVITY_CLI", "true").lower() in ("true", "1", "yes")
AGY_MODEL = os.getenv("AGY_MODEL", "gemini-3.8-flash-high")

# Fallback Google GenAI API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ComfyUI URLs
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "127.0.0.1")
COMFYUI_PORT = os.getenv("COMFYUI_PORT", "8188")
COMFYUI_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
COMFYUI_WS_URL = f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws"

# ComfyUI Directories
COMFYUI_INPUT_DIR = Path(os.getenv("COMFYUI_INPUT_DIR", r"F:\comfyui\ComfyUI_windows_portable\ComfyUI\input"))
COMFYUI_OUTPUT_DIR = Path(os.getenv("COMFYUI_OUTPUT_DIR", r"F:\comfyui\ComfyUI_windows_portable\ComfyUI\output"))

# Workflow 2 Group (Group 1: Qwen Image, Group 2: MiniMax H3 Video)
WORKFLOW_TEMPLATE_PATH = BASE_DIR / "qwen_minimax_workflow.json"
HOST_IMAGE_NAME = "host_character.jpg"
