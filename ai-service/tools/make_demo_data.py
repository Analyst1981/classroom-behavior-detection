# -*- coding: utf-8 -*-
"""生成端到端验证用演示素材（合成课堂场景图片 + 视频 + zip 批量包）。

用法：
    python tools/make_demo_data.py            # 生成到 ai-service/demo_data
    python tools/make_demo_data.py --n 8      # 指定图片数量
"""
from __future__ import annotations

import argparse
import random
import zipfile
from pathlib import Path

import numpy as np

try:
    import cv2
except Exception:
    cv2 = None

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "demo_data"
OUT.mkdir(exist_ok=True)

CLASSES = ["低头写字", "低头看书", "抬头听课", "转头", "举手", "站立"]


def draw_person(img, x, y, h, pose: int, rng: random.Random):
    """用几何图形绘制一个示意人物，pose 对应 6 类姿态。"""
    color_head = (222, 190, 160)
    color_body = (70 + rng.randint(0, 60), 90 + rng.randint(0, 60), 180 + rng.randint(0, 50))
    w = int(h * 0.28)
    # 身体
    cv2.rectangle(img, (x, y + int(h * 0.25)), (x + w, y + h), color_body, -1)
    # 头
    hr = int(h * 0.14)
    cx = x + w // 2
    head_y = y + int(h * 0.16)
    cv2.circle(img, (cx, head_y), hr, color_head, -1)
    # 姿态差异
    if pose == 0:  # 低头写字
        cv2.line(img, (x + int(w * 0.2), y + int(h * 0.45)), (cx + int(w * 0.2), y + int(h * 0.62)), (240, 240, 240), 4)
        cv2.rectangle(img, (cx - 20, y + int(h * 0.62)), (cx + 30, y + int(h * 0.70)), (250, 250, 245), -1)
    elif pose == 1:  # 低头看书
        cv2.rectangle(img, (cx - 25, y + int(h * 0.55)), (cx + 25, y + int(h * 0.68)), (245, 245, 235), -1)
    elif pose == 3:  # 转头（头部偏移 + 肩线倾斜）
        cv2.circle(img, (cx + int(hr * 0.8), head_y), hr, color_head, -1)
    elif pose == 4:  # 举手
        cv2.line(img, (x + w, y + int(h * 0.32)), (x + w + int(w * 0.5), y + int(h * 0.05)), color_body, 6)
    elif pose == 5:  # 站立（整体更高、腿部分离）
        cv2.line(img, (x + int(w * 0.3), y + h), (x + int(w * 0.3), y + int(h * 1.18)), color_body, 5)
        cv2.line(img, (x + int(w * 0.7), y + h), (x + int(w * 0.7), y + int(h * 1.18)), color_body, 5)
    return img


def make_image(rng: random.Random, idx: int) -> np.ndarray:
    img = np.full((720, 1280, 3), 236, dtype=np.uint8)
    cv2.rectangle(img, (0, 0), (1280, 90), (60, 72, 88), -1)  # 黑板
    for i in range(6):  # 课桌
        dx = 60 + i * 200
        cv2.rectangle(img, (dx, 480), (dx + 170, 560), (196, 164, 132), -1)
    count = rng.randint(2, 5)
    for k in range(count):
        pose = rng.randrange(len(CLASSES))
        x = 80 + rng.randint(0, 4) * 220
        y = 330 + rng.randint(0, 60)
        h = rng.randint(150, 210)
        draw_person(img, x, y, h, pose, rng)
    cv2.putText(img, f"demo-{idx}", (20, 700), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (90, 90, 90), 2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--video", action="store_true", default=True)
    args = ap.parse_args()

    if cv2 is None:
        raise SystemExit("需要 opencv：pip install opencv-python-headless")

    rng = random.Random(2026)
    paths = []
    for i in range(args.n):
        img = make_image(rng, i + 1)
        p = OUT / f"classroom_{i + 1:02d}.jpg"
        cv2.imwrite(str(p), img)
        paths.append(p)
    print(f"[demo] 已生成 {len(paths)} 张图片 -> {OUT}")

    zpath = OUT / "classroom_batch.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            zf.write(p, p.name)
    print(f"[demo] 批量压缩包 -> {zpath}")

    if args.video:
        vpath = OUT / "classroom_demo.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        vw = cv2.VideoWriter(str(vpath), fourcc, 12.0, (640, 360))
        for i in range(60):
            img = make_image(random.Random(100 + i), i % args.n + 1)
            vw.write(cv2.resize(img, (640, 360)))
        vw.release()
        print(f"[demo] 演示视频 -> {vpath}")


if __name__ == "__main__":
    main()
