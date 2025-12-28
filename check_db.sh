#!/bin/bash
# 檢查資料庫狀態的腳本

echo "========================================="
echo "檢查資料庫設定"
echo "========================================="

# 1. 檢查 data 目錄是否存在
echo -e "\n1. 檢查 data 目錄:"
if [ -d "./data" ]; then
    echo "✅ data 目錄存在"
    ls -lah ./data
else
    echo "❌ data 目錄不存在,需要建立"
    mkdir -p ./data
    echo "✅ 已建立 data 目錄"
fi

# 2. 檢查 users.db 是否存在
echo -e "\n2. 檢查 users.db 檔案:"
if [ -f "./data/users.db" ]; then
    echo "✅ users.db 存在"
    ls -lh ./data/users.db
    echo ""
    echo "資料庫大小: $(du -h ./data/users.db | cut -f1)"
else
    echo "⚠️  users.db 尚未建立 (第一次登入時會自動建立)"
fi

# 3. 檢查容器內的資料庫
echo -e "\n3. 檢查容器內的資料庫:"
docker exec stock-dash-web ls -lah /app/data/ 2>/dev/null || echo "⚠️  容器未運行"

# 4. 檢查資料庫內容(如果存在)
echo -e "\n4. 檢查資料庫內容:"
if [ -f "./data/users.db" ]; then
    echo "用戶數量:"
    docker exec stock-dash-web python3 -c "
from auth import db, User, init_auth
from flask import Flask
app = Flask(__name__)
init_auth(app)
with app.app_context():
    print(f'總用戶數: {User.query.count()}')
    users = User.query.all()
    for u in users:
        print(f'  - {u.email} ({u.provider}) - 建立於 {u.created_at}')
" 2>/dev/null || echo "無法讀取資料庫內容"
else
    echo "資料庫尚未建立"
fi

# 5. 檢查目錄權限
echo -e "\n5. 檢查目錄權限:"
ls -ld ./data

echo -e "\n========================================="
echo "檢查完成"
echo "========================================="
