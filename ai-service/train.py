# -*- coding: utf-8 -*-
"""课堂行为检测模型训练脚本。

用法：
    python train.py --data data/classroom.yaml --epochs 100 --imgsz 640 --batch 16

训练完成后把最优权重复制到 models/best.pt，服务启动时会自动加载该权重，
从而由「演示引擎 / 通用权重」切换为真正的 6 类课堂行为检测。
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(BASE / "data" / "classroom.yaml"))
    ap.add_argument("--weights", default="yolov8n.pt", help="预训练基础权重，可选 v5/8/11/12")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="", help="留空自动选择；如 0 / cpu")
    ap.add_argument("--project", default=str(BASE / "runs"))
    ap.add_argument("--name", default="classroom")
    args = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.weights)
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device or None,
        project=args.project,
        name=args.name,
        exist_ok=True,
    )

    best = Path(results.save_dir) / "weights" / "best.pt"
    if best.exists():
        target = MODEL_DIR / "best.pt"
        shutil.copy2(best, target)
        print(f"[train] 最优权重已复制到：{target}")
        print("[train] 重启 ai-service 即可加载新权重（engine=ultralytics, generic=False）")
    else:
        print(f"[train] 未找到 best.pt：{best}")


if __name__ == "__main__":
    main()
