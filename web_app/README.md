# 这份工作能去吗？· JD→短视频脚本 智能体（Web 版）

把一条 JD 变成可拍摄的求职类爆款短视频脚本：MODEL-001 评分 + 竖版分镜表 + 信息核验表 + 合规备注。
相比 Coze 版本，本版把**评分算术、来源词清洗、超范围拒答、检索日期**全部用 Python 代码保证，模型只负责写文案，彻底根治 Coze+GLM 上"算错分 / 出现'来源：知识库显示' / 不拒答 / 日期写死"等反复出现的坑。大模型改用 OpenAI 兼容接口，默认 OpenRouter（一个 key 调几十个模型，含免费模型）。

## 一、准备 API Key（免费）

1. **OpenRouter**（生成脚本内容，OpenAI 兼容接口，一个 key 调几十个模型）
   注册 https://openrouter.ai → 进 https://openrouter.ai/keys 拿 Key（默认带免费额度）。
   推荐免费模型 `google/gemma-2-9b-it`；想更强可换付费 `openai/gpt-4o-mini`。
   > 也支持智谱/DeepSeek/OpenAI 等任意 OpenAI 兼容服务，改 `.env` 里的 `LLM_BASE_URL` / `LLM_MODEL` 即可。
2. **Tavily**（联网搜索，可选但推荐）
   注册 https://tavily.com → 拿 API Key（免费额度）。不想联网可留空，自动降级为知识库+模型知识。

## 二、安装与配置

```bash
cd web_app
pip install -r requirements.txt

# 复制环境变量样例并填入 key（Windows PowerShell 用 copy 代替 cp）
copy .env.example .env
# 用记事本打开 .env，把 LLM_API_KEY / TAVILY_API_KEY 改成你自己的
```

> 安全提醒：`.env` 不要提交到公开仓库，key 只存在你本地/服务器环境变量。

## 三、本地运行（演示 / 录屏交作业）

```bash
python app.py
```

浏览器打开 http://localhost:5000 ，粘贴 JD → 点「生成脚本」。
先跑自测确认核心逻辑无误：

```bash
python test_core.py
```

## 四、发布给别人用（公开链接）

把项目推到 GitHub，连到 **Render / Railway / Fly.io**（都支持 Python Web 服务，有免费档）：
- 启动命令：`pip install -r requirements.txt && python app.py`
- 在平台后台设置环境变量 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`TAVILY_API_KEY`（key 放服务器，别人看不到）
- 部署完会得到一个公开网址，谁点开都能用。

> 免费额度注意：OpenRouter 免费模型与 Tavily 都有免费调用量，班级演示足够；如流量大再考虑付费。

## 五、项目结构

```
web_app/
├── app.py          # Flask 后端：编排流程 + 调大模型(OpenAI兼容) + JSON 解析
├── core.py         # ★确定性逻辑：算分 / 清洗来源词 / 拒答闸门 / 动态日期
├── kb.py           # 知识库加载 + 关键词检索（读本地 91 个 md）
├── search.py       # Tavily 联网搜索
├── prompt.py       # 系统提示词 + 覆盖范围 + 拒答/介绍话术
├── templates/
│   └── index.html  # 前端页面（粘贴 JD + 展示结果 + 复制）
├── test_core.py    # 无 key 自测（评分/清洗/拒答验证）
├── requirements.txt
├── .env.example
└── README.md
```

## 六、和 Coze 版的能力对照

| 能力 | Coze+GLM | 本 Web 版 |
|------|----------|-----------|
| 综合分计算 | 模型算，常飘（89 写成 81.65） | 代码算，永远准 |
| 来源词清洗 | 提示词压不住 | 正则 strip，必干净 |
| 超范围拒答 | 偶发不拒答 | 代码拦截，100% 稳 |
| 检索日期 | 写死/漏写 | datetime 动态，天天准 |
| 联网搜索 | 依赖平台工具 | Tavily，可控可溯源 |
| 发布给别人 | 分享链接 | 公开网址（部署后） |
