"""把口语化描述整理成模型能用的提示词。

先问本地小模型（127.0.0.1:8080）；它没起、或答得不像提示词，就退回规则法。
规则法只做三件事：删口语词、把碎片收拾成短语、补一句跟环境融合用的质量后缀。
"""
import json
import re
import urllib.request

LOCAL = "http://127.0.0.1:8080/v1/chat/completions"

FILLERS = ("我想", "我想要", "我希望", "帮我", "请帮我", "能不能", "可不可以", "可以",
           "麻烦", "的话", "一下", "一点", "稍微", "比较", "挺", "特别", "非常",
           "感觉", "好像", "就是", "然后", "那个", "这种", "那种", "看看")

# 这句是给"贴回原图"用的：让模型知道生成物要跟环境的光线质感对上
QUALITY = "写实摄影质感，自然光影过渡，与周围环境光线一致，细节清晰"

PUNCT = "。；;！!？?、\n"


def _rule_normalize(text, quality=True):
    s = text
    for p in PUNCT:
        s = s.replace(p, "，")
    parts = []
    for chunk in s.split("，"):
        chunk = chunk.strip()
        for f in FILLERS:
            chunk = chunk.replace(f, "")
        chunk = chunk.strip(" \u3000")
        if chunk:
            parts.append(chunk)
    out = re.sub("，{2,}", "，", "，".join(parts)).strip("，")
    if quality and out:
        out = out + "\n" + QUALITY
    return out


def _llm_normalize(text, timeout=25):
    ask = (
        "把下面这段口语化的创作描述改写成用于图像生成模型的中文提示词。"
        "只输出改写结果本身，不要解释，不要引号，不要分点，长度不超过 120 字。"
        "保留原作者想要的主体、数量、动作和光影，去掉语气词。\n\n" + text
    )
    body = json.dumps({
        "messages": [{"role": "user", "content": ask}],
        "temperature": 0.3,
        "max_tokens": 300,
    }).encode()
    req = urllib.request.Request(LOCAL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def _plausible(out):
    if not out or not 4 <= len(out) <= 400:
        return False
    bad = ("抱歉", "作为", "无法", "以下是", "改写：", "提示词：", "```")
    return not any(b in out for b in bad)


def normalize(text, use_llm=True):
    """返回 (提示词, 用的哪种方式: llm / rule / empty)。"""
    text = (text or "").strip()
    # 连点两次规范化不该把质量后缀叠两遍
    text = text.replace("\n" + QUALITY, "").replace(QUALITY, "").strip()
    if not text:
        return "", "empty"
    if use_llm:
        try:
            out = _llm_normalize(text)
            if _plausible(out):
                return out, "llm"
        except Exception:
            pass
    return _rule_normalize(text), "rule"
