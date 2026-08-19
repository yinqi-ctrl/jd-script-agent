"""
联网搜索（Tavily）
- 返回字符串列表，供拼进 prompt 作为真实来源上下文
- 无 key 时返回空列表（自动降级为仅知识库+模型知识）
"""
import os
import requests


def web_search(query: str, max_results: int = 5):
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return []
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
            },
            timeout=25,
        )
        data = r.json()
        out = []
        for it in data.get("results", []):
            title = it.get("title", "")
            content = it.get("content", "")
            url = it.get("url", "")
            out.append(f"【{title}】{content}\n来源链接：{url}")
        return out
    except Exception as e:
        return [f"(联网搜索暂不可用：{e})"]


if __name__ == "__main__":
    res = web_search("数据运营 2026 薪资 真实体验 避坑")
    print(f"获取到 {len(res)} 条搜索结果")
    for r in res[:2]:
        print(r[:120])
