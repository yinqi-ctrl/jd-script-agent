"""
知识库加载与检索
- 读取本地 91 个 markdown（含 YAML frontmatter）
- 按 JD 关键词做轻量相关性打分，返回 top 片段
不依赖重型分词库，纯 Python 实现，方便部署。
"""
import os
import re
import glob

# 相对路径：随项目一起部署，本地和云服务器都能用（不再写死 Windows 盘符）
DEFAULT_KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "知识库")

# 5 大类 in_scope 关键词，用于从 JD 抽取检索词
CATEGORY_KW = [
    "内容运营", "产品", "商业", "出海", "跨境", "增长", "数据", "运营",
    "品牌", "营销", "用户", "社群", "HR", "人力资源", "销售", "咨询",
    "供应链", "电商", "海外", "TikTok", "独立站", "外贸", "项目经理",
    "商业分析", "产品经理", "市场",
]


def load_kb(kb_dir: str = None):
    """返回 [{file, text}] 列表，已剥离 frontmatter。"""
    kb_dir = kb_dir or os.environ.get("KB_DIR", DEFAULT_KB_DIR)
    docs = []
    for fp in glob.glob(os.path.join(kb_dir, "**", "*.md"), recursive=True):
        try:
            with open(fp, encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        # 去掉 YAML frontmatter
        text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.S)
        docs.append({"file": os.path.basename(fp), "text": text})
    return docs


def chunk_text(text: str, size: int = 400):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if buf and len(buf) + len(p) > size:
            chunks.append(buf)
            buf = p
        else:
            buf = (buf + "\n" + p).strip()
    if buf:
        chunks.append(buf)
    return chunks


def extract_keywords(jd: str):
    kws = []
    for c in CATEGORY_KW:
        if c in jd:
            kws.append(c)
    # 尝试抓岗位名称（抓到空格/逗号/句号即止，避免贪长）
    m = re.search(r"岗位名称[】)\s:：]*[:：]?\s*([^\s，。,]{2,20})", jd)
    if m:
        kws.append(m.group(1).strip())
    # 兜底：取 JD 里的中文词片段
    if not kws:
        kws = list(dict.fromkeys(re.findall(r"[\u4e00-\u9fa5]{2,6}", jd)))[:8]
    return list(dict.fromkeys(kws))


def retrieve(jd: str, docs, top_k: int = 6):
    kws = extract_keywords(jd)
    scored = []
    for d in docs:
        # 跳过索引/汇总类文件（以下划线开头的 _INDEX.md 等），否则通用词会把它顶到最前
        if d["file"].startswith("_"):
            continue
        content = d["text"]
        score = 0
        for kw in kws:
            score += content.count(kw) * (3 if len(kw) >= 3 else 1)
        for kw in kws:
            if kw in d["file"]:
                score += 6
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    chunks = []
    for score, d in scored[:4]:
        for c in chunk_text(d["text"]):
            chunks.append({"file": d["file"], "text": c})
    # 按所属文件得分排序后取 top_k
    file_rank = {d["file"]: s for s, d in scored[:4]}
    chunks.sort(key=lambda x: -file_rank.get(x["file"], 0))
    return chunks[:top_k], kws


if __name__ == "__main__":
    d = load_kb()
    print(f"已加载 {len(d)} 个知识库文件")
    ch, kw = retrieve("【岗位名称】数据运营 薪资12-20K 负责埋点漏斗", d)
    print("检索词:", kw)
    for c in ch[:3]:
        print("-", c["file"], c["text"][:60])
