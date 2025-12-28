#!/usr/bin/env python3
"""
測試資料庫連線和用戶儲存功能
在容器內執行: docker exec -it stock-dash-web python3 test_db.py
"""

from auth import db, User, init_auth
from flask import Flask
import os

def test_database():
    """測試資料庫功能"""
    print("=" * 50)
    print("測試資料庫功能")
    print("=" * 50)

    # 建立 Flask app
    app = Flask(__name__)
    init_auth(app)

    with app.app_context():
        # 1. 檢查資料庫路徑
        db_path = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"\n1. 資料庫路徑: {db_path}")

        # 2. 檢查資料表是否存在
        try:
            user_count = User.query.count()
            print(f"\n2. ✅ 資料表存在,目前用戶數: {user_count}")
        except Exception as e:
            print(f"\n2. ❌ 資料表錯誤: {e}")
            print("   嘗試建立資料表...")
            db.create_all()
            print("   ✅ 資料表已建立")

        # 3. 列出所有用戶
        print("\n3. 現有用戶列表:")
        users = User.query.all()
        if users:
            for user in users:
                print(f"   - ID: {user.id}")
                print(f"     Email: {user.email}")
                print(f"     Name: {user.name}")
                print(f"     Provider: {user.provider}")
                print(f"     建立時間: {user.created_at}")
                print(f"     最後登入: {user.last_login}")
                print()
        else:
            print("   (無用戶資料)")

        # 4. 測試建立測試用戶
        test_email = "test@example.com"
        existing_test = User.query.filter_by(email=test_email).first()

        if not existing_test:
            print(f"\n4. 建立測試用戶 ({test_email})...")
            try:
                test_user = User(
                    oauth_id="google_test_123",
                    email=test_email,
                    name="測試用戶",
                    provider="google"
                )
                db.session.add(test_user)
                db.session.commit()
                print("   ✅ 測試用戶建立成功")
            except Exception as e:
                print(f"   ❌ 建立失敗: {e}")
                db.session.rollback()
        else:
            print(f"\n4. 測試用戶已存在: {existing_test.email}")

        # 5. 檢查資料庫檔案
        print("\n5. 檢查資料庫檔案:")
        db_file = db_path.replace('sqlite:///', '')
        if os.path.exists(db_file):
            file_size = os.path.getsize(db_file)
            print(f"   ✅ 檔案存在: {db_file}")
            print(f"   大小: {file_size} bytes ({file_size/1024:.2f} KB)")
        else:
            print(f"   ❌ 檔案不存在: {db_file}")

    print("\n" + "=" * 50)
    print("測試完成")
    print("=" * 50)

if __name__ == "__main__":
    test_database()
