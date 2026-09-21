# -*- coding: utf-8 -*-
"""PDF 报告生成。

优先使用 reportlab（注册 Adobe 中文字体 STSong-Light，无需外部字体文件）；
reportlab 不可用或字体注册失败时，回退到 Pillow 直接绘制 PDF，保证功能不中断。
"""
from __future__ import annotations

import io
import os
import time
from typing import Any, Dict

TITLE = "课堂行为智能检测报告"


def _payload(data: Dict[str, Any]) -> Dict[str, Any]:
    record = data.get("record") or data
    return {
        "id": record.get("id") or record.get("taskId") or "-",
        "type": record.get("type") or record.get("taskType") or "-",
        "source": record.get("source") or record.get("fileName") or "-",
        "createdAt": record.get("createdAt") or time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsedMs": record.get("elapsedMs") or record.get("elapsed") or 0,
        "count": record.get("count") or record.get("total") or 0,
        "perClass": record.get("perClass") or (record.get("stats") or {}).get("per_class") or {},
        "labels": record.get("labels") or [],
        "advice": record.get("advice") or record.get("aiAdvice") or "",
        "engine": record.get("engine") or "",
    }


def build_pdf(data: Dict[str, Any]) -> bytes:
    try:
        return _build_with_reportlab(_payload(data))
    except Exception:
        return _build_with_pillow(_payload(data))


# ------------------------- reportlab -------------------------
def _build_with_reportlab(p: Dict[str, Any]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font_name = "STSong-Light"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    except Exception:
        font_name = "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=16 * mm,
        title=TITLE, author="课堂行为智能检测系统",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontName=font_name, fontSize=18, leading=24)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=font_name, fontSize=13,
                        leading=18, spaceBefore=10, textColor=colors.HexColor("#1f4e79"))
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName=font_name, fontSize=10,
                          leading=15, alignment=TA_LEFT)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, textColor=colors.grey)

    story = [Paragraph(TITLE, h1), Spacer(1, 4)]

    total = int(p["count"] or 0) or sum(int(v) for v in p["perClass"].values()) or 0
    info = [
        ["记录编号", str(p["id"]), "检测类型", str(p["type"])],
        ["来源文件", str(p["source"]), "检测时间", str(p["createdAt"])],
        ["识别目标数", str(total), "推理耗时", f"{p['elapsedMs']} ms"],
    ]
    t = Table(info, colWidths=[26 * mm, 60 * mm, 26 * mm, 62 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3de")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f6fa")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f2f6fa")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [t, Spacer(1, 8)]

    story.append(Paragraph("一、行为类别统计", h2))
    rows = [["行为类别", "检出数量", "占比"]]
    for k, v in p["perClass"].items():
        ratio = f"{int(v) / total * 100:.1f}%" if total else "0%"
        rows.append([str(k), str(v), ratio])
    if len(rows) == 1:
        rows.append(["（无数据）", "0", "0%"])
    st = Table(rows, colWidths=[60 * mm, 40 * mm, 40 * mm])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3de")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [st, Spacer(1, 8)]

    story.append(Paragraph("二、检测明细（最多 20 条）", h2))
    detail = [["序号", "行为类别", "置信度", "位置(x1,y1,x2,y2)"]]
    for i, lb in enumerate(p["labels"][:20], 1):
        if isinstance(lb, dict):
            detail.append([
                str(i),
                str(lb.get("label", "-")),
                f"{float(lb.get('confidence', 0)):.2f}",
                ",".join(str(x) for x in lb.get("box", [])),
            ])
    if len(detail) == 1:
        detail.append(["-", "（无明细）", "-", "-"])
    dt = Table(detail, colWidths=[16 * mm, 40 * mm, 30 * mm, 68 * mm])
    dt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3de")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
        ("ALIGN", (0, 0), (2, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [dt, Spacer(1, 8)]

    story.append(Paragraph("三、AI 分析与教学建议", h2))
    advice = str(p["advice"]).strip() or "（未生成建议）"
    for line in advice.splitlines():
        line = line.strip()
        if not line:
            continue
        story.append(Paragraph(line.replace("<", "&lt;").replace(">", "&gt;"), body))
        story.append(Spacer(1, 2))

    story += [
        Spacer(1, 10),
        Paragraph(f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}　|　课堂行为智能检测系统", small),
    ]
    if p.get("engine") == "demo":
        story.append(Paragraph("注：本次报告基于演示引擎输出，仅供流程演示，不作为真实教学评价依据。", small))

    doc.build(story)
    return buf.getvalue()


# ------------------------- Pillow 回退 -------------------------
def _build_with_pillow(p: Dict[str, Any]) -> bytes:
    """无 reportlab 时的回退：用 Pillow 把文本内容绘制为多页 PDF。"""
    from PIL import Image, ImageDraw, ImageFont

    def font(size: int):
        for path in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
                     "C:/Windows/Fonts/simsun.ttc"):
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    W, H = 1240, 1754  # A4 @150dpi
    lines = [TITLE, ""]
    total = int(p["count"] or 0) or sum(int(v) for v in p["perClass"].values()) or 0
    lines += [
        f"记录编号：{p['id']}    检测类型：{p['type']}",
        f"来源文件：{p['source']}    时间：{p['createdAt']}",
        f"识别目标数：{total}    推理耗时：{p['elapsedMs']} ms",
        "",
        "一、行为类别统计",
    ]
    for k, v in p["perClass"].items():
        ratio = f"{int(v) / total * 100:.1f}%" if total else "0%"
        lines.append(f"    {k}：{v}（{ratio}）")
    lines += ["", "二、AI 分析与教学建议"]
    lines += ["    " + s for s in str(p["advice"]).splitlines()]
    if p.get("engine") == "demo":
        lines += ["", "注：本报告基于演示引擎输出，仅供流程演示。"]

    f_title, f_text = font(34), font(22)
    pages = []
    per_page = 40
    chunks = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[""]]
    for chunk in chunks:
        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)
        y = 80
        for i, line in enumerate(chunk):
            draw.text((80, y), line, font=f_title if i == 0 and chunk is chunks[0] else f_text,
                      fill=(25, 25, 25))
            y += 60 if (i == 0 and chunk is chunks[0]) else 40
        pages.append(img.convert("RGB"))

    buf = io.BytesIO()
    pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()
