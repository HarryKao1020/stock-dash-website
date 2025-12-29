#!/bin/bash
# 測試日誌清理功能

cd "$(dirname "$0")/.."

echo "🧪 測試日誌清理功能"
echo "===================="
echo ""

# 創建測試日誌目錄
mkdir -p logs

# 創建一些測試日誌檔案（模擬 8 天前的日誌）
echo "📝 創建測試日誌檔案..."

# 8 天前的日誌
touch -t $(date -v-8d +%Y%m%d0730) logs/$(date -v-8d +%Y%m%d)0730_log.txt
echo "舊日誌 (8天前)" > logs/$(date -v-8d +%Y%m%d)0730_log.txt

# 6 天前的日誌
touch -t $(date -v-6d +%Y%m%d0730) logs/$(date -v-6d +%Y%m%d)0730_log.txt
echo "舊日誌 (6天前)" > logs/$(date -v-6d +%Y%m%d)0730_log.txt

# 今天的日誌
touch logs/$(date +%Y%m%d)0730_log.txt
echo "最新日誌 (今天)" > logs/$(date +%Y%m%d)0730_log.txt

echo ""
echo "📂 清理前的日誌檔案:"
ls -lht logs/*_log.txt 2>/dev/null || echo "無日誌檔案"

echo ""
echo "🧹 執行清理測試..."
echo "（模擬：刪除 7 天前的日誌）"

# 這裡可以測試清理邏輯
for log_file in logs/*_log.txt; do
    if [ -f "$log_file" ]; then
        file_age=$(( ($(date +%s) - $(stat -f %m "$log_file")) / 86400 ))
        if [ $file_age -gt 7 ]; then
            echo "   🗑️  將刪除: $(basename "$log_file") (${file_age} 天前)"
        else
            echo "   ✅ 保留: $(basename "$log_file") (${file_age} 天前)"
        fi
    fi
done

echo ""
echo "✅ 測試完成！"
echo ""
echo "💡 提示: 實際執行 update_cache.py 會自動清理舊日誌"
