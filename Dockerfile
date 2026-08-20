FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY web_app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码和知识库
COPY web_app/ ./web_app/
COPY 知识库/ ./知识库/

# 环境变量
ENV PORT=7860
ENV PYTHONUNBUFFERED=1

# HF Spaces 要求非 root 用户运行
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

WORKDIR /app/web_app

# gunicorn 单 worker，超时 120 秒（LLM 调用可能较慢）
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120"]
