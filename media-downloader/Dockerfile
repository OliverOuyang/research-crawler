# 给 Coolify 用：构建上下文是 media-downloader/ 目录。
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mediadl ./mediadl
# 下载文件和 cookies 放挂载卷，容器重建不丢
ENV MEDIADL_OUT=/data MEDIADL_COOKIES_DIR=/cookies MEDIADL_KEEP_HOURS=72 PYTHONUNBUFFERED=1
VOLUME ["/data", "/cookies"]
EXPOSE 8765
# 容器内监听 0.0.0.0，由 Coolify 的反向代理接入；不要把端口直接发布到公网
CMD ["python", "-m", "mediadl", "serve", "--host", "0.0.0.0", "--port", "8765"]
