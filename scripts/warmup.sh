#!/bin/bash
#
# 資料預熱腳本
# 用途: 在交易日開盤前預先載入所有資料到記憶體快取
# 使用: ./scripts/warmup.sh
#

set -e

# 配置
APP_URL="${APP_URL:-http://localhost:8050}"
WARMUP_ENDPOINT="${APP_URL}/api/warmup"
LOG_DIR="${LOG_DIR:-./logs}"
LOG_FILE="${LOG_DIR}/warmup_$(date +%Y%m%d).log"

# 建立 log 目錄
mkdir -p "$LOG_DIR"

# 記錄開始時間
echo "======================================" | tee -a "$LOG_FILE"
echo "🔥 資料預熱開始: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "======================================" | tee -a "$LOG_FILE"

# 呼叫預熱 API
response=$(curl -s -w "\n%{http_code}" "$WARMUP_ENDPOINT" 2>&1)
http_code=$(echo "$response" | tail -n 1)
response_body=$(echo "$response" | sed '$d')

# 檢查 HTTP 狀態碼
if [ "$http_code" -eq 200 ]; then
    echo "✅ 預熱成功 (HTTP $http_code)" | tee -a "$LOG_FILE"
    echo "$response_body" | jq '.' 2>/dev/null | tee -a "$LOG_FILE" || echo "$response_body" | tee -a "$LOG_FILE"
else
    echo "❌ 預熱失敗 (HTTP $http_code)" | tee -a "$LOG_FILE"
    echo "$response_body" | tee -a "$LOG_FILE"
    exit 1
fi

echo "======================================" | tee -a "$LOG_FILE"
echo "🎉 預熱完成: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "======================================" | tee -a "$LOG_FILE"
