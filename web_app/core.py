"""
核心确定性逻辑（不依赖大模型，保证可控）
1. MODEL-001 V2 评分：Python 算分，根治 GLM 算术飘的问题
2. 来源词清洗：正则 strip，根治"来源：知识库显示"等 AI 味
3. out_of_scope 硬闸门：代码拦截，根治 Coze 拒答不稳
4. 动态日期：datetime 生成，根治写死日期
"""
import re
import datetime

WEIGHTS = {
    "d1": 0.35,  # 点击动机
    "d2": 0.10,  # 应届相关
    "d3": 0.25,  # 认知差（核心）
    "d4": 0.15,  # 讨论张力
    "d5": 0.10,  # 可拆解
    "d6": 0.05,  # 实用增量
}

OUT_OF_SCOPE_KW = [
    "医生", "医师", "护士", "律师", "公务员", "程序员", "后端开发", "前端开发",
    "算法", "算法工程师", "教师", "券商", "基金经理", "会计师", "会计", "法官",
    "警察", "军人", "药剂师", "建筑师", "飞行员",
]


def is_out_of_scope(jd: str) -> bool:
    """命中强专业资质/长期培养职业 → True（应拒答）。"""
    return any(kw in jd for kw in OUT_OF_SCOPE_KW)


def looks_like_jd(jd: str) -> bool:
    """简单启发：像 JD 才处理，否则当闲聊/问用法。"""
    jd = (jd or "").strip()
    if len(jd) < 15:
        return False
    markers = ["薪资", "职责", "任职要求", "公司", "工作地点", "招聘",
               "岗位", "JD", "要求", "职责描述", "岗位职责"]
    return any(m in jd for m in markers) or len(jd) >= 40


def compute_score(scores: dict) -> tuple:
    """
    scores: {"d1":int,...d6":int} 各 1-5
    返回 (综合分:float, 等级:str)
    综合分 = Σ(分×权重) × 20
    """
    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    raw = total * 20
    if raw >= 80:
        grade = "S"
    elif raw >= 65:
        grade = "A"
    elif raw >= 50:
        grade = "B"
    else:
        grade = "C"
    return round(raw, 1), grade


# 匹配：来源：xxx / 知识库显示/指出/提到 / 联网搜索显示 / 知识库-xxx
SOURCE_RE = re.compile(
    r"来源[:：]\s*[^\s，。、）)]*"
    r"|知识库[显示指出提到]+"
    r"|联网搜索[显示]+"
    r"|知识库[-—][^\s，。、）)]*"
)


def clean_script_text(text: str) -> str:
    """清除脚本正文（口播/字幕/镜头）里的来源转述套话。"""
    if not text:
        return text
    cleaned = SOURCE_RE.sub("", text)
    # 顺手把残留的空括号/多余空格收一下
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def today_str() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


if __name__ == "__main__":
    print("拒答测试:", is_out_of_scope("后端开发工程师 薪资高"))
    print("算分测试:", compute_score({"d1": 5, "d2": 4, "d3": 4, "d4": 4, "d5": 5, "d6": 4}),
          "(应为 89.0 S)")
    print("清洗测试:", clean_script_text("来源：知识库显示，这已是分析师配置"))
    print("日期:", today_str())
