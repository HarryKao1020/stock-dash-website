# 資料預熱腳本說明

## 問題背景

當第一個使用者訪問應用時,由於資料是 **lazy loading** (需要時才載入),會導致:
- FinLab 資料首次載入需要 10-30 秒
- Shioaji 即時資料首次載入需要 5-15 秒
- 使用者體驗不佳

## 解決方案: 預熱 API + Cron 排程

透過 **預熱 API** 在交易日開盤前預先載入所有資料到記憶體快取,確保使用者訪問時資料已準備好。

---

## 1. 預熱 API 端點

### 端點資訊
- **URL**: `GET /api/warmup`
- **功能**: 預先載入所有常用資料到記憶體
- **回應格式**: JSON

### 手動觸發

```bash
# 本地環境
curl http://localhost:8050/api/warmup

# 生產環境
curl http://your-domain.com/api/warmup
```

### 回應範例

```json
{
  "status": "success",
  "loaded": [
    "FinLab:收盤價 (2000 records)",
    "FinLab:成交量 (2000 records)",
    "FinLab:成交金額 (2000 records)",
    "FinLab:世界指數收盤價 (500 records)",
    "Shioaji:TSE (365 days)",
    "Shioaji:OTC (365 days)"
  ],
  "errors": [],
  "elapsed_seconds": 8.52
}
```

---

## 2. 使用預熱腳本

### 基本使用

```bash
# 執行預熱腳本
./scripts/warmup.sh

# 查看 log
tail -f logs/warmup_$(date +%Y%m%d).log
```

### 環境變數

```bash
# 自訂應用程式 URL
APP_URL=http://localhost:8050 ./scripts/warmup.sh

# 自訂 log 目錄
LOG_DIR=/var/log/stock-dash ./scripts/warmup.sh
```

---

## 3. 設定 Cron 自動排程

### 步驟 1: 複製 crontab 範例

```bash
cp scripts/crontab.example /tmp/stock-dash-cron
```

### 步驟 2: 修改路徑

編輯 `/tmp/stock-dash-cron`,將 `PROJECT_DIR` 改為你的實際專案路徑:

```bash
# 修改這一行
PROJECT_DIR=/Users/kaochenghong/Desktop/stock-dash-project
```

### 步驟 3: 安裝 crontab

```bash
# 安裝排程
crontab /tmp/stock-dash-cron

# 驗證是否安裝成功
crontab -l
```

### 步驟 4: 檢查 log

```bash
# 查看今天的預熱 log
tail -f logs/warmup_$(date +%Y%m%d).log

# 查看所有 log
ls -lh logs/warmup_*.log
```

---

## 4. 建議排程設定

### 方案 A: 每個交易日早上 8:00 (推薦)

```cron
0 8 * * 1-5 cd /path/to/project && ./scripts/warmup.sh
```

**適用情境**: 確保使用者在交易時段開始前資料已預載完成

### 方案 B: 早上 8:00 + 中午 12:00

```cron
0 8 * * 1-5 cd /path/to/project && ./scripts/warmup.sh
0 12 * * 1-5 cd /path/to/project && ./scripts/warmup.sh
```

**適用情境**: 確保午盤資料也是最新的

### 方案 C: 每 4 小時一次

```cron
0 */4 * * * cd /path/to/project && ./scripts/warmup.sh
```

**適用情境**: 搭配 `start_auto_refresh(interval_hours=4)` 使用,確保定時更新

---

## 5. Docker 環境設定

### 方法 1: Host 端 cron 直接呼叫 API

```cron
# 在 host 機器上設定 cron
0 8 * * 1-5 curl -s http://localhost:8050/api/warmup >> /var/log/stock-dash-warmup.log 2>&1
```

### 方法 2: 使用 docker exec

```cron
0 8 * * 1-5 docker exec stock-dash-app curl -s http://localhost:8050/api/warmup
```

### 方法 3: 在容器內設定 cron

修改 `Dockerfile` 安裝 cron:

```dockerfile
RUN apt-get update && apt-get install -y cron
COPY scripts/crontab.example /etc/cron.d/stock-dash-warmup
RUN chmod 0644 /etc/cron.d/stock-dash-warmup
RUN crontab /etc/cron.d/stock-dash-warmup
```

---

## 6. 驗證預熱是否成功

### 方法 1: 檢查 log

```bash
tail -f logs/warmup_$(date +%Y%m%d).log
```

成功的 log 範例:

```
======================================
🔥 資料預熱開始: 2025-01-15 08:00:01
======================================
✅ 預熱成功 (HTTP 200)
{
  "status": "success",
  "loaded": [
    "FinLab:收盤價 (2000 records)",
    ...
  ],
  "elapsed_seconds": 8.52
}
======================================
🎉 預熱完成: 2025-01-15 08:00:09
======================================
```

### 方法 2: 檢查應用程式 log

```bash
# Docker
docker-compose logs -f app

# 本地
tail -f logs/app.log
```

應該看到類似訊息:

```
🔥 預熱開始 - 載入 FinLab 資料...
✓ 讀取快取: price:收盤價
✓ 讀取快取: price:成交量
...
✅ 預熱完成! 耗時: 8.5 秒
```

### 方法 3: 測試首次訪問速度

```bash
# 清除瀏覽器快取後訪問
# 應該在 1-2 秒內載入完成,而不是 10-30 秒
```

---

## 7. 移除排程

```bash
# 列出目前的 crontab
crontab -l

# 移除所有排程
crontab -r

# 或編輯 crontab 手動刪除特定行
crontab -e
```

---

## 8. 常見問題

### Q1: cron 沒有執行?

檢查:
1. cron 服務是否運行: `sudo service cron status` (Linux) 或 `launchctl list | grep cron` (macOS)
2. 路徑是否正確: 使用絕對路徑,不要使用 `~` 或相對路徑
3. 腳本權限: `chmod +x scripts/warmup.sh`
4. cron log: `grep CRON /var/log/syslog` (Linux) 或 `log show --predicate 'process == "cron"'` (macOS)

### Q2: curl: command not found

安裝 curl:
```bash
# Ubuntu/Debian
sudo apt-get install curl

# macOS (通常已內建)
brew install curl
```

### Q3: 預熱失敗,HTTP 500

檢查:
1. 應用程式是否正在運行: `curl http://localhost:8050`
2. API 憑證是否正確: 檢查 `.env` 檔案
3. 應用程式 log: `docker-compose logs app` 或 `tail -f logs/app.log`

### Q4: Docker 容器啟動慢,影響預熱

建議使用 Docker healthcheck,確保容器完全啟動後才執行預熱:

```yaml
# docker-compose.yml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8050/api/warmup"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 9. 效能比較

| 情境 | 首次載入時間 | 說明 |
|------|-------------|------|
| **無預熱** | 15-30 秒 | 第一個使用者需等待所有 API 下載完成 |
| **有預熱** | 1-2 秒 | 資料已在記憶體,直接回傳 |
| **預熱耗時** | 5-15 秒 | 背景執行,不影響使用者 |

---

## 10. 建議工作流程

1. **開發環境**: 手動執行預熱即可
   ```bash
   ./scripts/warmup.sh
   ```

2. **生產環境**: 設定 cron 自動預熱
   ```bash
   # 每個交易日早上 8:00
   0 8 * * 1-5 cd /path/to/project && ./scripts/warmup.sh
   ```

3. **監控**: 定期檢查 log,確保預熱成功
   ```bash
   tail -f logs/warmup_*.log
   ```

---

## 參考資料

- [app.py](../app.py) - 預熱 API 實作
- [crontab.example](crontab.example) - Cron 設定範例
- [CLAUDE.md](../CLAUDE.md) - 專案架構說明
