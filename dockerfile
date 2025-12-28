# Dockerfile for Dash Financial Dashboard
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴 (TA-Lib 需要) + 設定時區
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    make \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 設定時區為台灣
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

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

# 啟動指令 - 針對 2GB RAM / 2 vCPUs 優化的 Gunicorn 設定
# --workers 1: 1 個 worker 進程（節省記憶體）
# --threads 4: 4 個執行緒（充分利用 2 vCPUs）
# --timeout 300: 5 分鐘超時（資料載入需要時間）
# --max-requests 1000: 每處理 1000 個請求後重啟 worker（防止記憶體洩漏）
# --max-requests-jitter 100: 隨機抖動避免同時重啟
# --worker-tmp-dir /dev/shm: 使用共享記憶體提升效能
# --access-logfile -: 輸出訪問日誌到 stdout
# --error-logfile -: 輸出錯誤日誌到 stderr
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8050", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "300", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:server"]