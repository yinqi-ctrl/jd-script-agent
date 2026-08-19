"""
Flask 后端：编排整个流程
JD → 拒答/闲聊判断 → 检索知识库 + 联网搜索 → 调 GLM 生成 → 代码算分 + 清洗 → 返回
"""
import os
import re
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from openai import OpenAI

import kb
import core
import search
import prompt

load_dotenv()
app = Flask(__name__)

# 大模型配置：兼容 OpenAI 协议的任意服务商（OpenRouter / 智谱 / DeepSeek / OpenAI 等）
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/gpt-4o-mini")
client = (
    OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://localhost",
            "X-Title": "JD-to-Script Agent",
        },
    )
    if LLM_API_KEY else None
)

_DOCS = None


def get_docs():
    global _DOCS
    if _DOCS is None:
        _DOCS = kb.load_kb()
    return _DOCS


_DESIGN = None


def get_design():
    global _DESIGN
    if _DESIGN is None:
        p = os.path.join(
            os.path.dirname(__file__), "..", "知识库",
            "短视频脚本模板库", "00_口播画面设计技巧.md",
        )
        try:
            with open(p, encoding="utf-8") as f:
                _DESIGN = f.read()
        except Exception:
            _DESIGN = ""
    return _DESIGN


def call_llm(jd: str, chunks: list, search_results: list, score_info: str) -> str:
    if not client:
        raise RuntimeError("未配置 LLM_API_KEY，无法调用大模型。请在 .env 填入后重启服务。")
    kb_text = "\n\n".join(f"[知识库片段·{c['file']}]\n{c['text']}" for c in chunks)
    search_text = (
        "\n\n".join(search_results)
        if search_results else "（本次未启用联网搜索，请基于知识库与你的知识作答）"
    )
    design_text = get_design()
    user_msg = f"""【选题价值评估结果】（系统已定，不可更改，脚本规格严格按此执行）：
{score_info}

用户JD：
{jd}

【知识库相关片段】（系统检索，供你引用事实，不要照抄"来源："前缀）：
{kb_text}

【联网搜索结果】（系统检索，供你引用事实与真实平台来源）：
{search_text}

【画面设计参考】（系统提供的口播短视频制作规范，务必遵循：构图/开头钩子/贴图花字/特效音效/节奏曲线/口播密度）：
{design_text}

请严格按系统提示词的 JSON 格式输出。"""
    req = dict(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": prompt.SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,  # 调低以稳定 6 维评分，避免同一 JD 分数随机漂移
    )
    # 仅当显式开启 JSON 模式时才传 response_format（部分 OpenRouter 免费模型不支持该参数）
    if os.environ.get("LLM_JSON_MODE", "false").lower() == "true":
        req["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**req)
    return resp.choices[0].message.content


def parse_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            return json.loads(m.group(0))
        raise


def extend_script(jd: str, script: list, need: int, chunks: list, search_results: list) -> list:
    """行数不足时自动追加补镜头调用：等级与脚本长度强绑定，不赌模型自觉。"""
    kb_text = "\n\n".join(f"[知识库片段·{c['file']}]\n{c['text']}" for c in chunks[:3])
    user_msg = f"""原始JD：
{jd}

【知识库补充片段】（供新增镜头引用事实）：
{kb_text}

【当前脚本 script 数组】（共 {len(script)} 行，要求补足到 {need} 行）：
{json.dumps(script, ensure_ascii=False)}

请按系统提示词补足镜头，返回完整 script 数组 JSON。"""
    req = dict(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": prompt.EXTEND_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
    )
    resp = client.chat.completions.create(**req)
    obj = parse_json(resp.choices[0].message.content)
    rows = obj if isinstance(obj, list) else obj.get("script", [])
    out = []
    for row in rows:
        out.append({
            "time": row.get("time", ""),
            "shot": core.clean_script_text(row.get("shot", "")),
            "voice": core.clean_script_text(row.get("voice", "")),
            "subtitle": core.clean_script_text(row.get("subtitle", "")),
            "tone": row.get("tone", ""),
        })
    # 补全结果行数必须不减少才采用，否则沿用原脚本
    return out if len(out) >= len(script) else script


def score_jd(jd: str) -> dict:
    """第一阶段：独立评分调用。只看 JD 本身评选题价值，temperature=0 完全可复现，
    且不接触脚本内容——脚本写得再好也不给 D3/D5 注水。"""
    if not client:
        raise RuntimeError("未配置 LLM_API_KEY，无法调用大模型。请在 .env 填入后重启服务。")
    req = dict(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": prompt.SCORING_PROMPT},
            {"role": "user", "content": f"待评估JD：\n{jd}\n\n请按系统提示词输出评分 JSON。"},
        ],
        temperature=0,  # 评分阶段：完全可复现
    )
    resp = client.chat.completions.create(**req)
    return parse_json(resp.choices[0].message.content)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/score", methods=["POST"])
def score():
    """阶段①：选题价值评估。S/A 建议制作，B/C 默认不做（用户坚持可再进阶段②）。"""
    data = request.get_json(force=True, silent=True) or {}
    jd = (data.get("jd") or "").strip()
    if not jd:
        return jsonify({"status": "error", "msg": "请输入 JD"})

    # 闲聊 / 问用法
    if not core.looks_like_jd(jd):
        return jsonify({"status": "ok", "type": "intro", "msg": prompt.INTRO_MSG})

    # 超范围硬闸门（代码拦截，100% 稳）
    if core.is_out_of_scope(jd):
        return jsonify({"status": "ok", "type": "reject", "msg": prompt.REJECT_MSG})

    try:
        obj = score_jd(jd)
        scores = {k: int(obj["scores"][k]) for k in core.WEIGHTS}
        total, grade = core.compute_score(scores)
        return jsonify({
            "status": "ok", "type": "score",
            "scores": scores, "total": total, "grade": grade,
            "direction": obj.get("direction", "类型4：普通介绍"),
            "plan": obj.get("plan", ""),
            "score_evidence": obj.get("score_evidence", {}) or {},
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": f"评估失败：{e}"})


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True, silent=True) or {}
    jd = (data.get("jd") or "").strip()
    if not jd:
        return jsonify({"status": "error", "msg": "请输入 JD"})

    # 闲聊 / 问用法
    if not core.looks_like_jd(jd):
        return jsonify({"status": "ok", "type": "intro", "msg": prompt.INTRO_MSG})

    # 超范围硬闸门（代码拦截，100% 稳）
    if core.is_out_of_scope(jd):
        return jsonify({"status": "ok", "type": "reject", "msg": prompt.REJECT_MSG})

    try:
        # 评分结果由阶段①产出、前端回传；总分与等级由代码重算（不信任客户端）
        score_data = data.get("score") or {}
        raw_scores = score_data.get("scores") or {}
        scores = {k: int(raw_scores.get(k, 3)) for k in core.WEIGHTS}
        total, grade = core.compute_score(scores)
        direction = score_data.get("direction", "类型4：普通介绍")
        plan = score_data.get("plan", "")
        score_evidence = score_data.get("score_evidence", {}) or {}
        score_info = (
            f"- 综合分：{total}（{grade}级）\n"
            f"- 内容方向：{direction}\n"
            f"- 六维评分：{json.dumps(scores, ensure_ascii=False)}\n"
            f"- 执行计划：{plan}"
        )

        docs = get_docs()
        chunks, kws = kb.retrieve(jd, docs)
        query = f"{(kws[0] if kws else jd)} 2026 薪资 真实体验 避坑"
        search_results = search.web_search(query) if os.environ.get("TAVILY_API_KEY") else []

        raw = call_llm(jd, chunks, search_results, score_info)
        obj = parse_json(raw)

        # ★ 代码清洗脚本正文（根治 AI 味来源套话）
        script = []
        for row in obj.get("script", []):
            script.append({
                "time": row.get("time", ""),
                "shot": core.clean_script_text(row.get("shot", "")),
                "voice": core.clean_script_text(row.get("voice", "")),
                "subtitle": core.clean_script_text(row.get("subtitle", "")),
                "tone": row.get("tone", ""),
            })

        # ★ 行数不足自动补镜头（S级≥12行 / A级≥10行 / B/C级≥8行）
        need = 12 if grade == "S" else (10 if grade == "A" else 8)
        if len(script) < need and client:
            try:
                script = extend_script(jd, script, need, chunks, search_results)
            except Exception:
                pass  # 补全失败沿用原脚本，不阻断主流程

        # ★ 代码补动态日期
        date = core.today_str()
        verification = [{
            "dimension": row.get("dimension", ""),
            "content": row.get("content", ""),
            "source": row.get("source", ""),
            "date": date,
        } for row in obj.get("verification", [])]

        compliance = obj.get("compliance", [])

        return jsonify({
            "status": "ok", "type": "result",
            "scores": scores, "total": total, "grade": grade,
            "direction": direction, "plan": plan,
            "score_evidence": score_evidence, "script": script,
            "verification": verification, "compliance": compliance,
            "kb_files": [c["file"] for c in chunks],
            "search_used": bool(search_results),
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": f"生成失败：{e}"})


@app.route("/api/revise", methods=["POST"])
def revise():
    """对话式修改：把上一轮完整结果 + 用户修改指令一起发给 LLM，只改涉及部分，其余逐字保留。"""
    data = request.get_json(force=True, silent=True) or {}
    jd = (data.get("jd") or "").strip()
    instruction = (data.get("instruction") or "").strip()
    result = data.get("result") or {}
    if not instruction:
        return jsonify({"status": "error", "msg": "请输入修改指令"})
    if not result or not result.get("script"):
        return jsonify({"status": "error", "msg": "没有可修改的脚本，请先生成"})
    if not client:
        return jsonify({"status": "error", "msg": "未配置 LLM_API_KEY，无法调用大模型"})

    try:
        current = {
            "direction": result.get("direction", ""),
            "script": result.get("script", []),
            "verification": result.get("verification", []),
            "compliance": result.get("compliance", []),
        }
        user_msg = f"""原始JD：
{jd}

【当前完整脚本 JSON】（未被指令涉及的镜头须逐字保留）：
{json.dumps(current, ensure_ascii=False)}

【用户修改指令】：
{instruction}

请按系统提示词返回修改后的完整 JSON（含 script、verification、compliance 三个键）。"""
        req = dict(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": prompt.REVISE_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
        resp = client.chat.completions.create(**req)
        obj = parse_json(resp.choices[0].message.content)

        # 合并：模型返回的键覆盖原结果，缺的沿用原值（评分与方向不参与修改）
        script_src = obj.get("script") or current["script"]
        script = []
        for row in script_src:
            script.append({
                "time": row.get("time", ""),
                "shot": core.clean_script_text(row.get("shot", "")),
                "voice": core.clean_script_text(row.get("voice", "")),
                "subtitle": core.clean_script_text(row.get("subtitle", "")),
                "tone": row.get("tone", ""),
            })

        ver_src = obj.get("verification") or current["verification"]
        date = core.today_str()
        verification = [{
            "dimension": row.get("dimension", ""),
            "content": row.get("content", ""),
            "source": row.get("source", ""),
            "date": date,
        } for row in ver_src]

        compliance = obj.get("compliance") or current["compliance"]

        return jsonify({
            "status": "ok", "type": "result",
            "scores": result.get("scores", {}),
            "total": result.get("total"),
            "grade": result.get("grade"),
            "direction": result.get("direction", ""),
            "plan": result.get("plan", ""),
            "score_evidence": result.get("score_evidence", {}),
            "script": script,
            "verification": verification,
            "compliance": compliance,
            "kb_files": result.get("kb_files", []),
            "search_used": result.get("search_used", False),
            "revised": instruction,
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": f"修改失败：{e}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"知识库文件数: {len(get_docs())}")
    print(f"LLM 客户端: {'已就绪' if client else '未配置 LLM_API_KEY'}")
    app.run(host="0.0.0.0", port=port, debug=False)
