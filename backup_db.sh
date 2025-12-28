#!/bin/bash
# 資料庫備份腳本
# 建議加入 crontab: 0 2 * * * /path/to/backup_db.sh

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="./data/users.db"

# 建立備份目錄
mkdir -p "$BACKUP_DIR"

# 備份資料庫
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_DIR/users_${DATE}.db"
    echo "✅ 資料庫已備份: $BACKUP_DIR/users_${DATE}.db"

    # 只保留最近 7 天的備份
    find "$BACKUP_DIR" -name "users_*.db" -mtime +7 -delete
    echo "✅ 舊備份已清理 (保留 7 天)"
else
    echo "❌ 找不到資料庫檔案: $DB_FILE"
fi
