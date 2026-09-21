# -*- coding: utf-8 -*-
"""大模型教学建议生成。

支持 DeepSeek 与 Qwen（均为 OpenAI 兼容协议）。
未配置 API Key 时自动使用本地规则引擎，保证系统在离线环境仍可完整演示。
"""
from __future__ import annotations

import json
from typing import Any, Dict

import requests

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_ALLOW_LOCAL_FALLBACK,
    LLM_PROVIDER,
    LLM_TIMEOUT,
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
)

PROFILES = {
    "deepseek": {"key": DEEPSEEK_API_KEY, "base_url": DEEPSEEK_BASE_URL, "model": DEEPSEEK_MODEL, "label": "DeepSeek"},
    "qwen": {"key": QWEN_API_KEY, "base_url": QWEN_BASE_URL, "model": QWEN_MODEL, "label": "Qwen"},
}

SYSTEM_PROMPT = (
    "你是一名资深课堂观察者与教学顾问。请基于给出的课堂行为检测统计结果，"
    "输出结构化的中文分析，包含：1) 学习状态评估；2) 课堂管理建议；3) 需要关注的学生群体；"
    "4) 下一步教学改进措施。要求条理清晰、可执行，不要复述原始数据。"
)


def build_payload(stats: Dict[str, Any], extra: str = "") -> str:
    return (
        "以下是本次课堂行为检测的统计结果（JSON）：\n"
        f"{json.dumps(stats, ensure_ascii=False, indent=2)}\n"
        + (f"补充信息：{extra}\n" if extra else "")
        + "请给出分析与建议。"
    )


def call_llm(stats: Dict[str, Any], extra: str = "", provider: str | None = None) -> Dict[str, Any]:
    provider = (provider or LLM_PROVIDER).lower()
    prof = PROFILES.get(provider, PROFILES["deepseek"])

    if not prof["key"]:
        if LLM_ALLOW_LOCAL_FALLBACK:
            text = local_advice(stats)
            return {"provider": "local", "model": "rule-engine", "content": text, "ok": True, "fallback": True}
        return {"provider": provider, "model": prof["model"], "content": "", "ok": False, "error": "未配置 API Key"}

    url = prof["base_url"].rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {prof['key']}", "Content-Type": "application/json"}
    body = {
        "model": prof["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_payload(stats, extra)},
        ],
        "temperature": 0.6,
        "max_tokens": 1200,
    }
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=LLM_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {"provider": provider, "model": prof["model"], "content": content, "ok": True, "fallback": False}
    except Exception as exc:
        if LLM_ALLOW_LOCAL_FALLBACK:
            return {
                "provider": "local",
                "model": "rule-engine",
                "content": local_advice(stats),
                "ok": True,
                "fallback": True,
                "error": f"{type(exc).__name__}: {exc}",
            }
        return {"provider": provider, "model": prof["model"], "content": "", "ok": False, "error": str(exc)}


def local_advice(stats: Dict[str, Any]) -> str:
    """本地规则引擎：依据各类别占比生成教学建议。"""
    total = int(stats.get("total", 0) or 0)
    per_class = stats.get("per_class") or {}
    if total == 0:
        return (
            "【学习状态评估】本次检测未识别到有效目标，建议检查画面角度、光照与检测阈值。\n"
            "【课堂管理建议】确认摄像头覆盖全场，适当提高置信度召回后重新采集。\n"
            "【需关注群体】暂无。\n"
            "【改进措施】重新采集样本并复核标注质量。"
        )

    def ratio(name: str) -> float:
        return float(per_class.get(name, 0)) / total

    listen = ratio("抬头听课")
    write = ratio("低头写字")
    read = ratio("低头看书")
    turn = ratio("转头")
    raise_hand = ratio("举手")
    stand = ratio("站立")

    if listen >= 0.6:
        state = "课堂整体专注度较高，多数学生处于抬头听课状态，教学节奏基本匹配学生接受能力。"
    elif listen >= 0.4:
        state = "课堂专注度中等，抬头听课比例尚可，但存在一定比例的非听课行为，需关注教学节奏。"
    else:
        state = "课堂专注度偏低，抬头听课比例不足，教学内容或节奏可能需要及时调整。"

    mgmt = []
    if turn >= 0.15:
        mgmt.append(f"转头行为占比 {turn:.0%}，提示存在交头接耳或外部干扰，建议加强巡课与目光覆盖。")
    if write + read >= 0.4:
        mgmt.append(f"书写/阅读合计占比 {write + read:.0%}，若发生在讲授环节，建议增加互动提问拉回注意力。")
    if raise_hand >= 0.1:
        mgmt.append(f"举手占比 {raise_hand:.0%}，互动意愿良好，建议保持并扩大提问覆盖面。")
    if stand >= 0.1:
        mgmt.append(f"站立占比 {stand:.0%}，需确认是否为展示环节，否则应规范课堂秩序。")
    if not mgmt:
        mgmt.append("各类非听课行为比例处于正常区间，维持现有课堂管理策略即可。")

    focus = []
    if turn >= 0.15:
        focus.append("频繁转头的学生（疑似注意力分散）")
    if write + read >= 0.4:
        focus.append("讲授环节持续低头书写/阅读的学生")
    if raise_hand < 0.05:
        focus.append("全程未参与互动的沉默学生")
    if not focus:
        focus.append("暂无明显高风险群体")

    actions = [
        "将本次统计按时间序列切片，定位专注度下降的具体时段并回溯教学环节。",
        "针对高频分心时段插入 2~3 分钟互动提问或随堂练习。",
        "持续积累多节课数据形成基线，用于班级纵向对比与教学效果评估。",
    ]

    return (
        f"【学习状态评估】{state}\n"
        f"【课堂管理建议】{'；'.join(mgmt)}\n"
        f"【需关注群体】{'、'.join(focus)}\n"
        f"【改进措施】{'；'.join(actions)}"
    )
