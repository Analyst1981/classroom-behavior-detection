# -*- coding: utf-8 -*-
"""视频与摄像头处理流水线。

- 后台线程逐帧推理，标注帧进入帧队列，供 MJPEG 实时流消费；
- 同时把标注后的帧写入输出文件：优先走 FFmpeg 管道编码为 H.264 MP4，
  FFmpeg 不可用时回退 OpenCV 的 mp4v 编码；
- 通过回调上报进度（供 SocketIO / 轮询使用）。
"""
from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

from config import (
    CAMERA_INDEX,
    FFMPEG_BIN,
    OUTPUT_DIR,
    STREAM_QUEUE_MAX,
    VIDEO_FPS_FALLBACK,
)

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class FrameTask:
    task_id: str
    kind: str  # video | camera
    source: str
    frames: "queue.Queue" = field(default_factory=lambda: queue.Queue(maxsize=STREAM_QUEUE_MAX))
    status: str = "running"  # running | finished | error | stopped
    progress: float = 0.0
    total_frames: int = 0
    processed: int = 0
    fps: float = 0.0
    error: str = ""
    output_file: str = ""
    stats: Dict[str, int] = field(default_factory=dict)
    per_frame: List[Dict] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    record: bool = False
    _stop_flag: bool = False

    def stop(self):
        self._stop_flag = True

    def to_dict(self) -> Dict:
        return {
            "taskId": self.task_id,
            "kind": self.kind,
            "source": self.source,
            "status": self.status,
            "progress": round(self.progress, 2),
            "totalFrames": self.total_frames,
            "processed": self.processed,
            "fps": round(self.fps, 2),
            "error": self.error,
            "outputFile": os.path.basename(self.output_file) if self.output_file else "",
            "outputUrl": (f"/static/outputs/{os.path.basename(self.output_file)}"
                          if self.output_file else ""),
            "stats": self.stats,
            "elapsedMs": int((time.time() - self.started_at) * 1000),
            "record": self.record,
        }


class TaskManager:
    """统一管理视频/摄像头任务。"""

    def __init__(self, detector, on_progress: Optional[Callable[[FrameTask], None]] = None):
        self.detector = detector
        self.tasks: Dict[str, FrameTask] = {}
        self.on_progress = on_progress or (lambda t: None)
        self._lock = threading.Lock()

    def create(self, kind: str, source: str, record: bool = False) -> FrameTask:
        task = FrameTask(task_id=_new_id(), kind=kind, source=source, record=record)
        with self._lock:
            self.tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> Optional[FrameTask]:
        return self.tasks.get(task_id)

    def remove(self, task_id: str):
        with self._lock:
            self.tasks.pop(task_id, None)

    def _emit(self, task: FrameTask):
        try:
            self.on_progress(task)
        except Exception:
            pass

    # ---------------- 视频 ----------------
    def start_video(self, task: FrameTask, src_path: str, out_name: str):
        def runner():
            cap = None
            writer = None
            proc = None
            try:
                cap = cv2.VideoCapture(src_path)
                if not cap.isOpened():
                    task.status = "error"
                    task.error = "无法打开视频文件（编码不受支持或文件损坏）"
                    self._emit(task)
                    return
                fps = cap.get(cv2.CAP_PROP_FPS) or VIDEO_FPS_FALLBACK
                if not fps or fps <= 0 or fps > 120:
                    fps = VIDEO_FPS_FALLBACK
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                task.total_frames = total
                task.fps = fps

                out_path = str(OUTPUT_DIR / out_name)
                # 输出容器根据编码器能力决定
                use_ffmpeg = _ffmpeg_available()
                if use_ffmpeg:
                    final_path = out_path if out_path.lower().endswith(".mp4") else out_path + ".mp4"
                    proc = subprocess.Popen(
                        [
                            FFMPEG_BIN, "-y",
                            "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{width}x{height}", "-r", str(fps),
                            "-i", "-",
                            "-an", "-c:v", "libx264", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                            final_path,
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    final_path = out_path if out_path.lower().endswith(".mp4") else out_path + ".mp4"
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(final_path, fourcc, fps, (width, height))

                idx = 0
                t0 = time.time()
                while True:
                    if task._stop_flag:
                        task.status = "stopped"
                        break
                    ok, frame = cap.read()
                    if not ok:
                        break
                    dets = self.detector.predict(frame)
                    for d in dets:
                        task.stats[d.label] = task.stats.get(d.label, 0) + 1
                    task.per_frame.append(
                        {
                            "frame": idx,
                            "timeSec": round(idx / fps, 2),
                            "count": len(dets),
                            "labels": [d.label for d in dets],
                        }
                    )
                    # 每 5 帧抽样保存，避免结果体过大
                    annotated = self.detector.annotate(frame, dets)
                    if proc is not None:
                        try:
                            proc.stdin.write(annotated.tobytes())
                        except Exception:
                            use_ffmpeg = False
                    if writer is not None:
                        writer.write(annotated)

                    try:
                        task.frames.put_nowait(annotated)
                    except queue.Full:
                        pass

                    idx += 1
                    task.processed = idx
                    task.progress = (idx / total * 100) if total else min(99.0, idx / 60.0 * 100)
                    if idx % max(1, int(fps)) == 0:
                        self._emit(task)
                task.output_file = final_path
                task.fps = round(idx / max(0.001, time.time() - t0), 2) if idx else fps
                if task.status == "running":
                    task.status = "finished"
                    task.progress = 100.0
            except Exception as exc:
                task.status = "error"
                task.error = f"{type(exc).__name__}: {exc}"
            finally:
                try:
                    if proc is not None:
                        proc.stdin.close()
                        proc.wait(timeout=15)
                except Exception:
                    pass
                if writer is not None:
                    writer.release()
                if cap is not None:
                    cap.release()
                self._emit(task)

        threading.Thread(target=runner, daemon=True).start()
        return task

    # ---------------- 摄像头 ----------------
    def start_camera(self, task: FrameTask, index: int = CAMERA_INDEX):
        def runner():
            cap = None
            writer = None
            try:
                cap = cv2.VideoCapture(index)
                if not cap.isOpened():
                    task.status = "error"
                    task.error = f"无法打开摄像头 index={index}"
                    self._emit(task)
                    return
                fps = cap.get(cv2.CAP_PROP_FPS) or VIDEO_FPS_FALLBACK
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
                task.fps = fps
                if task.record:
                    out_path = str(OUTPUT_DIR / f"camera_{task.task_id}.mp4")
                    if _ffmpeg_available():
                        writer = subprocess.Popen(
                            [
                                FFMPEG_BIN, "-y",
                                "-f", "rawvideo", "-pix_fmt", "bgr24",
                                "-s", f"{width}x{height}", "-r", str(fps),
                                "-i", "-", "-an",
                                "-c:v", "libx264", "-preset", "veryfast",
                                "-pix_fmt", "yuv420p", out_path,
                            ],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    else:
                        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
                    task.output_file = out_path
                idx = 0
                while not task._stop_flag:
                    ok, frame = cap.read()
                    if not ok:
                        task.status = "error"
                        task.error = "摄像头读取中断"
                        break
                    dets = self.detector.predict(frame)
                    for d in dets:
                        task.stats[d.label] = task.stats.get(d.label, 0) + 1
                    annotated = self.detector.annotate(frame, dets)
                    if writer is not None:
                        try:
                            if isinstance(writer, subprocess.Popen):
                                writer.stdin.write(annotated.tobytes())
                            else:
                                writer.write(annotated)
                        except Exception:
                            writer = None
                    try:
                        task.frames.put_nowait(annotated)
                    except queue.Full:
                        pass
                    idx += 1
                    task.processed = idx
                    task.progress = 100.0
                    if idx % max(1, int(fps or 25)) == 0:
                        self._emit(task)
                if task.status == "running":
                    task.status = "stopped"
            except Exception as exc:
                task.status = "error"
                task.error = f"{type(exc).__name__}: {exc}"
            finally:
                try:
                    if isinstance(writer, subprocess.Popen):
                        writer.stdin.close()
                        writer.wait(timeout=10)
                    elif writer is not None:
                        writer.release()
                except Exception:
                    pass
                if cap is not None:
                    cap.release()
                self._emit(task)

        threading.Thread(target=runner, daemon=True).start()
        return task


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(
            [FFMPEG_BIN, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=True,
        )
        return True
    except Exception:
        return False


def mjpeg_stream(task: FrameTask, timeout: float = 30.0, max_frames: Optional[int] = None):
    """从帧队列持续产出 MJPEG（multipart/x-mixed-replace）。"""
    if cv2 is None:
        return
    deadline = time.time() + timeout
    sent = 0
    last = None
    while True:
        if max_frames is not None and sent >= max_frames:
            return
        try:
            frame = task.frames.get(timeout=1.0)
            last = frame
        except queue.Empty:
            if task.status in ("finished", "error", "stopped") and time.time() > deadline - timeout + 2:
                # 任务结束后队列排空即退出
                if task.frames.empty():
                    return
            if time.time() > deadline:
                return
            continue
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ok:
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(buf)).encode() + b"\r\n\r\n" + buf.tobytes() + b"\r\n"
        )
        sent += 1
