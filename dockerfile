# Dockerfile for Dash Financial Dashboard
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴 (TA-Lib 需要)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    make \
    && rm -rf /var/lib/apt/lists/*

# 安裝 TA-Lib C library
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 建立 data/cache 目錄（快取檔案存放位置）
RUN mkdir -p data/cache

# 暴露端口
EXPOSE 8050

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 啟動指令 - 使用優化的 Gunicorn 設定
# --workers 1: 2GB RAM 建議用 1 個 worker
# --threads 2: 每個 worker 2 個 thread
# --timeout 300: 允許較長的啟動時間（載入資料）
# Dockerfile 最後一行改成
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "1", "--threads", "2", "--timeout", "300", "app:server"]