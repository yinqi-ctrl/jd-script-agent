"""
无 key 自测：验证评分 / 清洗 / 拒答 / 日期 的确定性
直接运行：python test_core.py
"""
from core import compute_score, clean_script_text, is_out_of_scope, looks_like_jd, today_str

passed, failed = 0, 0


def check(name, got, expect):
    global passed, failed
    ok = got == expect
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: got={got} expect={expect}")
    if ok:
        passed += 1
    else:
        failed += 1


# 1) 评分正确性（数据运营那次：正确应为 89.0 / S）
s = {"d1": 5, "d2": 4, "d3": 4, "d4": 4, "d5": 5, "d6": 4}
total, grade = compute_score(s)
check("评分 5/4/4/4/5/4 -> 总分", total, 89.0)
check("评分 5/4/4/4/5/4 -> 等级", grade, "S")

# 边界：79 -> A
check("评分 79分->A", compute_score({"d1":4,"d2":4,"d3":4,"d4":3,"d5":5,"d6":4})[0], 79.0)
check("评分 79分->等级A", compute_score({"d1":4,"d2":4,"d3":4,"d4":3,"d5":5,"d6":4})[1], "A")

# 2) 来源词清洗（Coze 上怎么都压不住的 AI 味）
cases = {
    "来源：知识库显示，这已是分析师配置": "，这已是分析师配置",
    "联网搜索显示，大部分初级数据运营在取数": "，大部分初级数据运营在取数",
    "来源：知识库指出，埋点没埋好": "，埋点没埋好",
    "来源：知识库-技术门槛。先看门槛": "。先看门槛",
}
for inp, exp in cases.items():
    check(f"清洗「{inp[:12]}…」", clean_script_text(inp), exp)

# 3) 拒答硬闸门
check("后端开发 拒答", is_out_of_scope("后端开发工程师 薪资高"), True)
check("律师 拒答", is_out_of_scope("某律所 律师助理"), True)
check("数据运营 不拒答", is_out_of_scope("数据运营 12-20K"), False)

# 4) 闲聊判断
check("闲聊不处理", looks_like_jd("你好，你是做什么的"), False)
check("JD 处理", looks_like_jd("【岗位名称】数据运营 薪资12-20K 职责埋点"), True)

# 5) 动态日期
print(f"[INFO] 今天日期：{today_str()}（应为真实当天，绝不写死）")

print(f"\n结果：{passed} 通过 / {failed} 失败")
