#!/bin/bash
# 監控資料庫健康狀態

DB_FILE="./data/users.db"

echo "========================================="
echo "資料庫健康檢查"
echo "時間: $(date)"
echo "========================================="

# 檢查檔案是否存在
if [ ! -f "$DB_FILE" ]; then
    echo "❌ 錯誤: 資料庫檔案不存在!"
    echo "   路徑: $DB_FILE"
    exit 1
fi

echo "✅ 資料庫檔案存在"
echo "   路徑: $DB_FILE"
echo "   大小: $(du -h $DB_FILE | cut -f1)"
echo "   修改時間: $(stat -c %y $DB_FILE 2>/dev/null || stat -f %Sm $DB_FILE)"

# 檢查檔案完整性
echo ""
echo "檢查資料庫完整性..."
if sqlite3 "$DB_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "✅ 資料庫完整性正常"
else
    echo "❌ 警告: 資料庫可能損壞!"
fi

# 統計資料
echo ""
echo "資料統計:"
USER_COUNT=$(docker exec stock-dash-web python3 -c "
from auth import db, User, init_auth
from flask import Flask
app = Flask(__name__)
init_auth(app)
with app.app_context():
    print(User.query.count())
" 2>/dev/null)

if [ ! -z "$USER_COUNT" ]; then
    echo "   用戶總數: $USER_COUNT"
else
    echo "   無法讀取用戶數量"
fi

echo "========================================="
