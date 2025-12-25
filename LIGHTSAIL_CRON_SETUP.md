# Lightsail Docker 環境 Cron 設定指南

## 📋 概述

在 Lightsail 上透過 Docker 運行應用程式時，需要在**宿主機**（Lightsail instance）設定 cron，讓它定期呼叫 Docker 容器內的腳本。

## 🚀 快速安裝步驟

### 1. SSH 連線到 Lightsail

```bash
ssh -i /path/to/your-key.pem ubuntu@your-lightsail-ip
```

### 2. 確認 Docker 容器名稱

```bash
cd /path/to/stock-dash-project
docker-compose ps
```

預期輸出類似：
```
NAME                        COMMAND                  SERVICE   STATUS
stock-dash-project-web-1    "gunicorn --bind 0.0…"   web       Up
```

記下容器名稱（例如：`stock-dash-project-web-1`）

### 3. 測試手動執行（重要！）

```bash
# 方法 A: 使用 docker-compose（推薦）
cd /path/to/stock-dash-project
docker-compose exec -T web python scripts/update_cache.py

# 方法 B: 使用 docker exec
docker exec stock-dash-project-web-1 python scripts/update_cache.py
```

確認沒有錯誤後再繼續。

### 4. 建立 logs 目錄

```bash
cd /path/to/stock-dash-project
mkdir -p logs
```

### 5. 複製並修改 crontab 設定

```bash
# 複製範例檔案
cp scripts/crontab.example /tmp/stock-dash-cron

# 用編輯器修改路徑
nano /tmp/stock-dash-cron
```

**必須修改的部分**（第 25 行）：
```bash
# 改成你的實際專案路徑
PROJECT_DIR=/home/ubuntu/stock-dash-project
```

如果容器名稱不是預設的，也要修改第 55-58 行的容器名稱。

### 6. 安裝 crontab

```bash
crontab /tmp/stock-dash-cron
```

### 7. 驗證安裝

```bash
# 查看已安裝的 cron 任務
crontab -l

# 檢查 cron 服務狀態
sudo systemctl status cron
```

## 📅 排程時間說明

已設定 4 個時段自動更新快取：

| 時間 | 說明 | Cron 表達式 |
|------|------|-------------|
| 07:30 | 開盤前更新資料 | `30 7 * * 1-5` |
| 13:45 | 盤中更新（午休後） | `45 13 * * 1-5` |
| 17:30 | 收盤後更新當日完整資料 | `30 17 * * 1-5` |
| 00:00 | 深夜更新（確保隔日資料完整） | `0 0 * * *` |

**注意**：
- `1-5` 表示週一到週五（交易日）
- 半夜 00:00 的任務為 `* * *`（每天執行，包含週末）

## 🔍 監控與除錯

### 查看執行日誌

```bash
# 即時監控日誌
tail -f /path/to/stock-dash-project/logs/cache_update.log

# 查看最近 50 行
tail -n 50 /path/to/stock-dash-project/logs/cache_update.log

# 搜尋錯誤訊息
grep -i "error\|failed\|❌" /path/to/stock-dash-project/logs/cache_update.log
```

### 手動觸發測試

```bash
# 測試完整流程（包含路徑切換）
cd /path/to/stock-dash-project && docker-compose exec -T web python scripts/update_cache.py
```

### 檢查 cron 是否執行

```bash
# 查看系統 cron 日誌（Ubuntu/Debian）
sudo grep CRON /var/log/syslog | tail -n 20

# 或使用 journalctl
sudo journalctl -u cron -n 20
```

### 常見問題排查

1. **Cron 沒有執行**
   ```bash
   # 確認 cron 服務運行
   sudo systemctl status cron

   # 重啟 cron 服務
   sudo systemctl restart cron
   ```

2. **找不到 docker-compose 指令**
   ```bash
   # 在 crontab 中指定完整路徑
   PATH=/usr/local/bin:/usr/bin:/bin
   ```

3. **容器未運行**
   ```bash
   # 確認容器狀態
   docker-compose ps

   # 啟動容器
   docker-compose up -d
   ```

4. **權限問題**
   ```bash
   # 確保 logs 目錄可寫入
   chmod 755 /path/to/stock-dash-project/logs
   ```

## 🛠️ 進階設定

### 調整執行時間

編輯 crontab：
```bash
crontab -e
```

修改時間後儲存即可，無需重啟 cron 服務。

### 只保留特定時段

如果不需要 4 個時段，可以註解掉不要的行：
```bash
crontab -e

# 用 # 註解掉不需要的排程
# 45 13 * * 1-5 cd $PROJECT_DIR && docker-compose exec -T web python scripts/update_cache.py >> $LOG_DIR/cache_update.log 2>&1
```

### 調整日誌保留

在 crontab 中加入日誌清理（每月清理 30 天前的日誌）：
```bash
# 在 crontab -e 中新增
0 2 1 * * find /path/to/stock-dash-project/logs -name "*.log" -mtime +30 -delete
```

### 移除所有排程

```bash
# 完全移除 crontab
crontab -r

# 或編輯清空
crontab -e
# （刪除所有內容後儲存）
```

## 📊 驗證快取更新

### 檢查快取檔案時間戳

```bash
# 查看最近更新的 Parquet 檔案
ls -lht /path/to/stock-dash-project/cache/*.parquet | head -n 10
```

### 檢查快取目錄大小

```bash
du -sh /path/to/stock-dash-project/cache
```

預期大小：80-160 MB（Parquet 格式）

## 🔔 Email 通知（可選）

如果想在排程執行時收到 Email 通知：

```bash
crontab -e

# 在檔案開頭加入
MAILTO=your-email@example.com

# 之後的排程如果有輸出或錯誤，會自動寄信
```

**注意**：需要先設定系統的 mail 服務（如 sendmail 或 postfix）。

## 📝 完整範例

```bash
# /tmp/stock-dash-cron 完整內容範例

SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
PROJECT_DIR=/home/ubuntu/stock-dash-project
LOG_DIR=$PROJECT_DIR/logs

# 多時段更新快取
30 7 * * 1-5 cd $PROJECT_DIR && docker-compose exec -T web python scripts/update_cache.py >> $LOG_DIR/cache_update.log 2>&1
45 13 * * 1-5 cd $PROJECT_DIR && docker-compose exec -T web python scripts/update_cache.py >> $LOG_DIR/cache_update.log 2>&1
30 17 * * 1-5 cd $PROJECT_DIR && docker-compose exec -T web python scripts/update_cache.py >> $LOG_DIR/cache_update.log 2>&1
0 0 * * * cd $PROJECT_DIR && docker-compose exec -T web python scripts/update_cache.py >> $LOG_DIR/cache_update.log 2>&1

# 每月清理舊日誌
0 2 1 * * find $LOG_DIR -name "*.log" -mtime +30 -delete
```

## ✅ 檢查清單

- [ ] SSH 連線到 Lightsail
- [ ] 確認 Docker 容器運行中
- [ ] 測試手動執行腳本成功
- [ ] 建立 logs 目錄
- [ ] 修改 PROJECT_DIR 路徑
- [ ] 安裝 crontab
- [ ] 驗證 crontab 已載入（`crontab -l`）
- [ ] 等待下一個排程時間，檢查日誌檔案
- [ ] 確認快取檔案時間戳更新

## 🎯 推薦時區設定

確認系統時區正確：

```bash
# 查看目前時區
timedatectl

# 設定為台北時區（如果不正確）
sudo timedatectl set-timezone Asia/Taipei
```

這樣 cron 的時間才會是台灣時間（如 07:30 就是台北早上 7:30）。
