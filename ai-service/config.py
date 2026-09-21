# -*- coding: utf-8 -*-
"""全局配置：所有可调参数集中在此，优先读取环境变量。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

# ---------- 路径 ----------
OUTPUT_DIR = Path(os.getenv("CBD_OUTPUT_DIR", str(BASE_DIR / "outputs")))
MODEL_DIR = Path(os.getenv("CBD_MODEL_DIR", str(BASE_DIR / "models")))
UPLOAD_DIR = Path(os.getenv("CBD_UPLOAD_DIR", str(BASE_DIR / "uploads")))
for _d in (OUTPUT_DIR, MODEL_DIR, UPLOAD_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------- 课堂行为类别（与原文一致，6 类） ----------
# 顺序即模型训练时的 class id 顺序，修改后需同步 data/classroom.yaml
CLASS_NAMES = [
    "低头写字",   # 0
    "低头看书",   # 1
    "抬头听课",   # 2
    "转头",       # 3
    "举手",       # 4
    "站立",       # 5
]
CLASS_NAMES_EN = [
    "writing", "reading", "listening", "turning_head", "hand_raising", "standing",
]

# ---------- 模型 ----------
# 主权重：自己训练的课堂行为权重（best.pt）。不存在时自动回退。
MODEL_WEIGHTS = os.getenv("CBD_MODEL_WEIGHTS", str(MODEL_DIR / "best.pt"))
# 回退权重：ultralytics 官方通用权重，可自动下载（约 6MB）
FALLBACK_WEIGHTS = os.getenv("CBD_FALLBACK_WEIGHTS", "yolov8n.pt")
# 当 PyTorch / ultralytics 不可用时，是否允许使用内置演示检测引擎（保证链路可跑通）
ALLOW_DEMO_ENGINE = os.getenv("CBD_ALLOW_DEMO_ENGINE", "1") not in ("0", "false", "False")

CONF_THRES = float(os.getenv("CBD_CONF_THRES", "0.25"))
IOU_THRES = float(os.getenv("CBD_IOU_THRES", "0.45"))
IMG_SIZE = int(os.getenv("CBD_IMGSIZE", "640"))
DEVICE = os.getenv("CBD_DEVICE", "auto")  # auto / cpu / cuda:0

# ---------- 大模型（DeepSeek / Qwen） ----------
# 两者均为 OpenAI 兼容协议，仅 base_url / model 不同
LLM_PROVIDER = os.getenv("CBD_LLM_PROVIDER", "deepseek").lower()  # deepseek | qwen
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
QWEN_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")
LLM_TIMEOUT = int(os.getenv("CBD_LLM_TIMEOUT", "60"))
# 未配置 API Key 时，使用本地规则引擎生成建议（保证功能可用）
LLM_ALLOW_LOCAL_FALLBACK = os.getenv("CBD_LLM_ALLOW_LOCAL_FALLBACK", "1") not in ("0", "false", "False")

# ---------- 视频 / 摄像头 ----------
VIDEO_FPS_FALLBACK = float(os.getenv("CBD_VIDEO_FPS", "25"))
CAMERA_INDEX = int(os.getenv("CBD_CAMERA_INDEX", "0"))
FFMPEG_BIN = os.getenv("CBD_FFMPEG", "ffmpeg")
# 实时流帧队列最大长度（防止内存无限增长）
STREAM_QUEUE_MAX = int(os.getenv("CBD_STREAM_QUEUE_MAX", "30"))

# ---------- 服务 ----------
HOST = os.getenv("CBD_AI_HOST", "0.0.0.0")
PORT = int(os.getenv("CBD_AI_PORT", "5000"))
# 允许访问的静态结果目录（供 Spring Boot / 前端直接拉取图片视频）
STATIC_ROUTE = "/static/outputs"

# ---------- 绘制 ----------
# 每类一个颜色（BGR）
CLASS_COLORS = [
    (56, 90, 240),    # 低头写字
    (32, 165, 218),   # 低头看书
    (86, 180, 60),    # 抬头听课
    (240, 176, 40),   # 转头
    (208, 90, 200),   # 举手
    (70, 120, 235),   # 站立
]

# ---------- CORS ----------
CORS_ORIGINS = os.getenv("CBD_CORS_ORIGINS", "*")
