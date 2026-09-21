# -*- coding: utf-8 -*-
"""课堂行为智能检测系统 —— AI 推理服务（Flask + PyTorch/YOLO）。

对外接口（Spring Boot 与前端均可直接调用）：
  GET  /health                      健康检查
  GET  /api/model/status            模型与运行模式
  POST /api/detect/image            单张图片检测
  POST /api/detect/batch            图片文件夹批量检测（多文件 / zip）
  POST /api/detect/video            上传视频 → 异步任务
  GET  /api/video/stream/<id>       MJPEG 实时流
  GET  /api/task/<id>               任务状态与统计
  POST /api/camera/start            打开摄像头
  GET  /api/camera/stream/<id>      摄像头 MJPEG 流
  POST /api/camera/stop/<id>        关闭摄像头
  POST /api/ai/advice               DeepSeek / Qwen 教学建议
  POST /api/report/pdf              生成 PDF 报告
  GET  /static/outputs/<file>       结果文件
"""
from __future__ import annotations

import base64
import io
import os
import threading
import time
import zipfile
from typing import List

import numpy as np
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import (
    CORS_ORIGINS,
    HOST,
    OUTPUT_DIR,
    PORT,
    STATIC_ROUTE,
    UPLOAD_DIR,
    CLASS_NAMES,
)
from detector import DETECTOR, Detection

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

from report import build_pdf
from video_pipeline import TaskManager, mjpeg_stream

app = Flask(__name__)
CORS(app, origins=CORS_ORIGINS.split(",") if CORS_ORIGINS != "*" else "*")

# SocketIO 为可选能力：环境不支持时自动降级为轮询
socketio = None
try:
    from flask_socketio import SocketIO, emit  # noqa

    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
except Exception as exc:  # pragma: no cover
    socketio = None


def _on_progress(task):
    if socketio is not None:
        try:
            socketio.emit("progress", task.to_dict())
        except Exception:
            pass


TASKS = TaskManager(DETECTOR, on_progress=_on_progress)

ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
ALLOWED_VIDEO = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"}


# ---------------- 工具 ----------------
def _ext(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def _read_image(file_storage) -> np.ndarray:
    data = file_storage.read()
    if cv2 is None:
        raise RuntimeError("OpenCV 不可用，无法解码图片")
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("图片解码失败，请确认文件格式")
    return img


def _summarize(dets: List[Detection]) -> dict:
    per_class = {name: 0 for name in CLASS_NAMES}
    for d in dets:
        per_class[d.label] = per_class.get(d.label, 0) + 1
    confs = [d.confidence for d in dets]
    return {
        "total": len(dets),
        "per_class": per_class,
        "avgConfidence": round(sum(confs) / len(confs), 4) if confs else 0.0,
        "maxConfidence": round(max(confs), 4) if confs else 0.0,
    }


def _save_image(img: np.ndarray, prefix: str = "img") -> str:
    name = f"{prefix}_{int(time.time() * 1000)}.jpg"
    path = OUTPUT_DIR / name
    cv2.imwrite(str(path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return name


def _to_data_uri(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


# ---------------- 基础接口 ----------------
@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "ai-service", "engine": DETECTOR.engine_name,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S")})


@app.get("/api/model/status")
def model_status():
    return jsonify(DETECTOR.status())


@app.get("/api/classes")
def classes():
    return jsonify({"classes": CLASS_NAMES})


# ---------------- 单张图片 ----------------
@app.post("/api/detect/image")
def detect_image():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "缺少 file 字段"}), 400
    f = request.files["file"]
    try:
        img = _read_image(f)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    t0 = time.perf_counter()
    dets = DETECTOR.predict(img)
    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    annotated = DETECTOR.annotate(img, dets)
    name = _save_image(annotated, "single")

    return jsonify({
        "ok": True,
        "engine": DETECTOR.engine_name,
        "outImage": _to_data_uri(annotated),
        "outImg": f"{STATIC_ROUTE}/{name}",
        "outUrl": f"{STATIC_ROUTE}/{name}",
        "fileName": secure_filename(f.filename),
        "width": int(img.shape[1]),
        "height": int(img.shape[0]),
        "labels": [d.to_dict() for d in dets],
        "count": len(dets),
        "stats": _summarize(dets),
        "elapsedMs": elapsed,
    })


# ---------------- 批量（图片文件夹） ----------------
@app.post("/api/detect/batch")
def detect_batch():
    files = request.files.getlist("files")
    if not files:
        # 兼容不同客户端/网关使用的字段名
        files = request.files.getlist("file")
    zip_file = request.files.get("zip")
    if zip_file is None or not zip_file.filename:
        for f in files:
            if f.filename and f.filename.lower().endswith(".zip"):
                zip_file = f
                break
    items = []  # (filename, image)

    if zip_file and zip_file.filename:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_file.read())) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    if _ext(info.filename) not in ALLOWED_IMAGE:
                        continue
                    if "__MACOSX" in info.filename or info.filename.startswith("."):
                        continue
                    data = zf.read(info)
                    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
                        items.append((os.path.basename(info.filename), img))
        except Exception as exc:
            return jsonify({"ok": False, "error": f"zip 解析失败：{exc}"}), 400
    else:
        for f in files:
            if not f.filename or _ext(f.filename) not in ALLOWED_IMAGE:
                continue
            try:
                items.append((secure_filename(f.filename), _read_image(f)))
            except Exception:
                continue

    if not items:
        return jsonify({"ok": False, "error": "未接收到有效图片"}), 400

    t0 = time.perf_counter()
    results = []
    agg = {name: 0 for name in CLASS_NAMES}
    total = 0
    for fname, img in items:
        dets = DETECTOR.predict(img)
        annotated = DETECTOR.annotate(img, dets)
        name = _save_image(annotated, "batch")
        stats = _summarize(dets)
        for k, v in stats["per_class"].items():
            agg[k] = agg.get(k, 0) + v
        total += len(dets)
        results.append({
            "fileName": fname,
            "count": len(dets),
            "labels": [d.to_dict() for d in dets],
            "stats": stats,
            "outUrl": f"{STATIC_ROUTE}/{name}",
            "outImage": _to_data_uri(annotated),
        })
    elapsed = round((time.perf_counter() - t0) * 1000, 2)

    return jsonify({
        "ok": True,
        "engine": DETECTOR.engine_name,
        "totalImages": len(items),
        "totalDetections": total,
        "perClass": agg,
        "elapsedMs": elapsed,
        "results": results,
    })


# ---------------- 视频 ----------------
@app.post("/api/detect/video")
def detect_video():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "缺少 file 字段"}), 400
    f = request.files["file"]
    if _ext(f.filename) not in ALLOWED_VIDEO:
        return jsonify({"ok": False, "error": f"不支持的视频格式：{f.filename}"}), 400
    src = UPLOAD_DIR / f"video_{int(time.time() * 1000)}_{secure_filename(f.filename)}"
    f.save(str(src))
    out_name = f"out_{int(time.time() * 1000)}.mp4"
    task = TASKS.create("video", secure_filename(f.filename))
    TASKS.start_video(task, str(src), out_name)
    return jsonify({"ok": True, "taskId": task.task_id, "status": task.status})


@app.get("/api/video/stream/<task_id>")
def video_stream(task_id):
    task = TASKS.get(task_id)
    if task is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    return Response(
        mjpeg_stream(task, timeout=600),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ---------------- 摄像头 ----------------
@app.post("/api/camera/start")
def camera_start():
    data = request.get_json(silent=True) or {}
    index = int(data.get("index", 0))
    record = bool(data.get("record", False))
    task = TASKS.create("camera", f"camera:{index}", record=record)
    TASKS.start_camera(task, index)
    return jsonify({"ok": True, "taskId": task.task_id, "record": record})


@app.post("/api/camera/stop/<task_id>")
def camera_stop(task_id):
    task = TASKS.get(task_id)
    if task is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    task.stop()
    return jsonify({"ok": True, "taskId": task_id, "status": task.status})


@app.get("/api/camera/stream/<task_id>")
def camera_stream(task_id):
    task = TASKS.get(task_id)
    if task is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    return Response(
        mjpeg_stream(task, timeout=3600),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ---------------- 任务状态 ----------------
@app.get("/api/task/<task_id>")
def task_status(task_id):
    task = TASKS.get(task_id)
    if task is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    d = task.to_dict()
    d["ok"] = True
    d["statsSummary"] = {
        "total": sum(task.stats.values()),
        "per_class": task.stats,
    }
    return jsonify(d)


# ---------------- AI 建议 ----------------
@app.post("/api/ai/advice")
def ai_advice():
    from llm import call_llm  # 延迟导入，避免启动时依赖网络配置

    data = request.get_json(silent=True) or {}
    stats = data.get("stats") or {}
    extra = data.get("extra", "")
    provider = data.get("provider")
    result = call_llm(stats, extra, provider)
    result["ok"] = True
    return jsonify(result)


# ---------------- PDF 报告 ----------------
@app.post("/api/report/pdf")
def report_pdf():
    data = request.get_json(silent=True) or {}
    try:
        pdf_bytes = build_pdf(data)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"PDF 生成失败：{exc}"}), 500
    filename = f"report_{int(time.time() * 1000)}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------- 静态结果 ----------------
@app.get(STATIC_ROUTE + "/<path:filename>")
def static_outputs(filename):
    return send_from_directory(str(OUTPUT_DIR), filename)


if __name__ == "__main__":
    print(f"[ai-service] engine={DETECTOR.engine_name} weights={DETECTOR.weights_used}")
    threading.Thread(target=DETECTOR.warmup, daemon=True).start()
    print(f"[ai-service] listening on http://{HOST}:{PORT}")
    if socketio is not None:
        socketio.run(app, host=HOST, port=PORT, debug=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host=HOST, port=PORT, debug=False, threaded=True)
