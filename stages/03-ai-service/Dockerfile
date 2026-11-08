FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com

# 基础依赖 + 推流依赖（opencv/numpy），保证 MJPEG 画面可用
COPY requirements.txt requirements-stream.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-stream.txt

COPY app ./app

# 回放数据目录：运维用 docker cp 往里放 JSON，必须预先建好并授权给运行用户
RUN useradd -m -u 10001 appuser \
    && mkdir -p /app/artifacts \
    && chown -R appuser:appuser /app/artifacts

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
