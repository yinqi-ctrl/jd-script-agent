#!/usr/bin/env python3
# 把《这份工作能去吗？》知识库的事实类条目（JD/EXP/IND/CASE）转换为扣子(Coze)可上传的纯文本。
# 处理：删除 YAML frontmatter，首行写「类型/类别/角色」便于范围筛选；正文原样保留。
import os, re, pathlib

SRC = pathlib.Path(r"d:/桌面/智能体作业/知识库")
OUT = pathlib.Path(r"d:/桌面/智能体作业/扣子部署包/知识库纯文本")
OUT.mkdir(parents=True, exist_ok=True)

def split_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)

def get_field(fm, key):
    m = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", fm, re.MULTILINE)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")

stats = {"jd": 0, "exp": 0, "ind": 0, "case": 0, "skip_nofm": 0, "skip_nocov": 0}
for p in sorted(SRC.rglob("*.md")):
    rel = p.relative_to(SRC)
    # 只处理四类事实条目目录
    parts = rel.parts
    if not (parts[0] in ("岗位JD数据库", "职业真实体验数据库", "行业趋势与职业发展数据库")
            or (parts[0] == "爆款职业类短视频案例库" and parts[1] == "cases")):
        continue
    text = p.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        stats["skip_nofm"] += 1
        continue
    cs = get_field(fm, "coverage_status")
    if not cs:
        stats["skip_nocov"] += 1
        continue
    cat = get_field(fm, "scope_category")
    role = get_field(fm, "scope_role")
    header = f"# 类型:{cs} 类别:{cat} 角色:{role}\n\n"
    out_body = body.strip() + "\n"
    out_path = OUT / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + out_body, encoding="utf-8")
    if parts[0] == "岗位JD数据库":
        stats["jd"] += 1
    elif parts[0] == "职业真实体验数据库":
        stats["exp"] += 1
    elif parts[0] == "行业趋势与职业发展数据库":
        stats["ind"] += 1
    else:
        stats["case"] += 1

print("转换完成：", stats)
print("输出目录：", OUT)
