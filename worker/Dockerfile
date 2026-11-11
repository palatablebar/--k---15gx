# 构建上下文是项目根目录（需要同时拿到 backend/ 与 worker/）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai \
    PYTHONPATH=/app:/app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# worker 复用 backend 的依赖与业务代码（算法只有一份实现，避免漂移）
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 60 -r /app/requirements.txt

COPY backend /app/backend
COPY worker/src /app/worker_src
COPY worker/healthcheck.sh /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh && mkdir -p /data/artifacts

WORKDIR /app
CMD ["celery", "-A", "worker_src.config.celery_app", "worker", "-B", "-l", "info", "--concurrency=2"]
