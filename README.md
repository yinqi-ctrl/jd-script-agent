---
title: JD Script Agent
emoji: 🎬
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# 这份工作能去吗？· JD→短视频脚本

粘贴一条招聘 JD，系统自动评估选题价值并生成竖版分镜短视频脚本。

## 功能流程

1. **选题价值评估**：六维评分 + 等级判定（S/A/B/C）+ 内容方向建议
2. **脚本生成**：仅 S/A 级触发，输出竖版分镜表（时长/画面/口播/字幕/语气）
3. **信息核验表**：每条信息标注来源与检索日期
4. **合规标注**：风险标签自动标注

## 技术栈

- 后端：Flask + Gunicorn
- 大模型：DeepSeek-V3（SiliconFlow）
- 联网搜索：Tavily API
- 知识库：6 大模块（JD库/体验库/行业趋势/案例库/脚本模板/评分模型）
