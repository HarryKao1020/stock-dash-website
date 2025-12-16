# 台股儀表板 - OAuth 登入整合指南

## 📋 概述

本指南說明如何在你的 Dash 台股儀表板中整合 Google 和 Facebook OAuth 登入功能。

---

## 🔧 步驟一：申請 OAuth 憑證

### Google OAuth 申請

1. **前往 Google Cloud Console**
   - 網址：https://console.cloud.google.com/

2. **建立專案**
   - 點選左上角專案選擇器 → **New Project**
   - 專案名稱：`taiwan-stock-dashboard`
   - 點選 **Create**

3. **設定 OAuth 同意畫面**
   - 左側選單：**APIs & Services → OAuth consent screen**
   - User Type：選擇 **External**
   - 填寫資訊：
     - App name：`台股儀表板`
     - User support email：你的 Email
     - Authorized domains：你的網域（例如 `yourdomain.com`）
     - Developer contact email：你的 Email
   - Scopes：新增 `email`, `profile`, `openid`
   - Test users：新增測試帳號（發布前使用）

4. **建立 OAuth 憑證**
   - 左側選單：**APIs & Services → Credentials**
   - 點選 **+ Create Credentials → OAuth client ID**
   - Application type：**Web application**
   - Name：`台股儀表板 Web Client`
   - Authorized JavaScript origins：
     ```
     http://localhost:8050
     https://yourdomain.com
     ```
   - Authorized redirect URIs：
     ```
     http://localhost:8050/auth/google/callback
     https://yourdomain.com/auth/google/callback
     ```
   - 點選 **Create**
   - 記下 **Client ID** 和 **Client Secret**

### Facebook OAuth 申請

1. **前往 Facebook Developers**
   - 網址：https://developers.facebook.com/

2. **建立應用程式**
   - 點選 **My Apps → Create App**
   - 選擇 **Consumer** 或 **Set up Facebook Login**
   - App name：`台股儀表板`
   - App contact email：你的 Email
   - 點選 **Create App**

3. **設定 Facebook Login**
   - Dashboard 左側：**Add Products**
   - 找到 **Facebook Login** → **Set Up**
   - 選擇 **Web**
   - Site URL：`https://yourdomain.com`

4. **設定 OAuth 重導向 URI**
   - 進入 **Facebook Login → Settings**
   - Valid OAuth Redirect URIs：
     ```
     http://localhost:8050/auth/facebook/callback
     https://yourdomain.com/auth/facebook/callback
     ```
   - 點選 **Save Changes**

5. **取得憑證**
   - 進入 **Settings → Basic**
   - 記下 **App ID** 和 **App Secret**
   - 填寫：
     - App Domains：`yourdomain.com`
     - Privacy Policy URL：你的隱私權政策頁面
     - Data Deletion Instructions URL：資料刪除說明頁面

6. **發布應用程式**
   - 頂部切換 **Development** → **Live**
   - 需要完成商業驗證才能讓所有用戶使用

---

## 🔧 步驟二：安裝套件

```bash
pip install authlib flask-login requests
```

或更新 requirements.txt：

```txt
authlib>=1.3.0
flask-login>=0.6.3
requests>=2.31.0
```

---

## 🔧 步驟三：設定環境變數

複製 `.env.example` 為 `.env`，填入你的憑證：

```bash
cp .env.example .env
```

編輯 `.env`：

```env
# Flask 密鑰
SECRET_KEY=your-super-secret-key-here

# Google OAuth
GOOGLE_CLIENT_ID=123456789-xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxx

# Facebook OAuth
FACEBOOK_CLIENT_ID=1234567890
FACEBOOK_CLIENT_SECRET=abcdefghijklmnop

# 其他設定
LOGIN_REQUIRED=false
```

---

## 🔧 步驟四：整合到你的 app.py

### 方法一：最小修改（推薦）

只需在你現有的 `app.py` 中加入以下程式碼：

```python
# 在檔案開頭匯入
from auth import init_auth

# 在建立 app 之後、layout 之前加入
server = app.server
init_auth(server)
```

### 方法二：完整整合（包含 UI）

參考 `app_with_auth.py` 的完整範例，包含：
- 側邊欄用戶狀態顯示
- 手機版用戶資訊
- 登入/登出按鈕

---

## 📁 檔案結構

```
your-project/
├── app.py              # 主應用程式（需修改）
├── auth.py             # 🆕 OAuth 認證模組
├── user_components.py  # 🆕 用戶 UI 元件
├── .env                # 🆕 環境變數（不要上傳 git）
├── .env.example        # 🆕 環境變數範例
├── requirements.txt    # 更新：加入 authlib, flask-login
├── pages/
│   ├── home.py
│   ├── kline.py
│   └── ...
└── assets/
    └── styles.css
```

---

## 🌐 Docker 部署設定

更新你的 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  dash-app:
    build: .
    container_name: dash-financial-dashboard
    ports:
      - "8050:8050"
    environment:
      - FINLAB_TOKEN=${FINLAB_TOKEN}
      - API_KEY=${API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      # 🆕 OAuth 環境變數
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - FACEBOOK_CLIENT_ID=${FACEBOOK_CLIENT_ID}
      - FACEBOOK_CLIENT_SECRET=${FACEBOOK_CLIENT_SECRET}
      - LOGIN_REQUIRED=${LOGIN_REQUIRED:-false}
    volumes:
      - ./cache:/app/cache
    restart: unless-stopped
```

---

## 🔐 認證流程

```
用戶點擊「Google 登入」
        ↓
重導向到 Google 授權頁面
        ↓
用戶同意授權
        ↓
Google 重導向回 /auth/google/callback
        ↓
auth.py 處理 callback，取得用戶資訊
        ↓
建立 session，登入成功
        ↓
重導向回首頁
```

---

## 🛡️ 安全注意事項

1. **永遠不要將 `.env` 上傳到 Git**
   ```gitignore
   # .gitignore
   .env
   ```

2. **使用 HTTPS**（正式環境必須）
   - Google 和 Facebook 都要求 redirect URI 使用 HTTPS
   - 本地開發可用 `http://localhost`

3. **定期更換 SECRET_KEY**
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

4. **限制授權範圍**
   - 只請求必要的 scope（email, profile）

---

## 🐛 常見問題

### 1. redirect_uri_mismatch 錯誤

**原因**：Callback URL 不匹配

**解決**：確認 Google/Facebook 後台設定的 redirect URI 完全一致：
- 包含 `http://` 或 `https://`
- 包含正確的 port
- 路徑完全一致（`/auth/google/callback`）

### 2. Facebook 登入只有測試用戶能用

**原因**：App 還在 Development 模式

**解決**：
1. 完成隱私權政策設定
2. 切換到 Live 模式
3. 如需完整權限，完成 Business Verification

### 3. Session 失效太快

**原因**：SECRET_KEY 變更或未設定

**解決**：
```env
SECRET_KEY=固定的密鑰不要每次都產生新的
```

---

## 📚 相關資源

- [Google OAuth 2.0 文件](https://developers.google.com/identity/protocols/oauth2)
- [Facebook Login 文件](https://developers.facebook.com/docs/facebook-login/)
- [Authlib 文件](https://docs.authlib.org/)
- [Flask-Login 文件](https://flask-login.readthedocs.io/)

---

## 🎉 完成！

整合完成後，你的應用程式將有：
- `/auth/login` - 登入頁面
- `/auth/google` - Google 登入
- `/auth/facebook` - Facebook 登入
- `/auth/logout` - 登出
- `/auth/user` - 取得當前用戶資訊（API）