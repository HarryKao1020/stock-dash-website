"""
OAuth 認證模組 - Google & Facebook 登入
使用 SQLite 儲存用戶資料
適用於 Dash + Flask 應用程式
"""

import os
import secrets
from datetime import datetime
from functools import wraps
from flask import redirect, url_for, session, request, Blueprint
from authlib.integrations.flask_client import OAuth
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from flask_sqlalchemy import SQLAlchemy

# ============================================
# 資料庫設定
# ============================================
db = SQLAlchemy()


# ============================================
# 設定類別
# ============================================
class AuthConfig:
    """認證設定"""

    # Flask 密鑰（用於 session 加密）
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

    # SQLite 資料庫路徑
    # 預設放在專案的 data 目錄下
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_DIR = os.environ.get("DB_DIR", os.path.join(BASE_DIR, "data"))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f'sqlite:///{os.path.join(DB_DIR, "users.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google OAuth 設定
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Facebook OAuth 設定
    FACEBOOK_CLIENT_ID = os.environ.get("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET = os.environ.get("FACEBOOK_CLIENT_SECRET", "")

    # 登入後導向的頁面
    LOGIN_REDIRECT_URL = "/"

    # 是否需要登入才能使用
    LOGIN_REQUIRED = os.environ.get("LOGIN_REQUIRED", "false").lower() == "true"


# ============================================
# 用戶模型（SQLAlchemy）
# ============================================
class User(UserMixin, db.Model):
    """用戶資料表"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    oauth_id = db.Column(
        db.String(100), unique=True, nullable=False
    )  # google_xxx 或 facebook_xxx
    email = db.Column(db.String(120), nullable=True)
    name = db.Column(db.String(100), nullable=True)
    picture = db.Column(db.String(500), nullable=True)
    provider = db.Column(db.String(20), nullable=False)  # 'google' 或 'facebook'

    # 時間戳記
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

    # 額外資訊（可選）
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<User {self.email}>"

    @classmethod
    def get_by_oauth_id(cls, oauth_id):
        """根據 OAuth ID 取得用戶"""
        return cls.query.filter_by(oauth_id=oauth_id).first()

    @classmethod
    def get_or_create(cls, oauth_id, email, name, picture=None, provider=None):
        """取得或建立用戶"""
        user = cls.get_by_oauth_id(oauth_id)

        if user:
            # 更新最後登入時間和資料
            user.last_login = datetime.utcnow()
            user.name = name or user.name
            user.picture = picture or user.picture
            if email:
                user.email = email
            db.session.commit()
        else:
            # 建立新用戶
            user = cls(
                oauth_id=oauth_id,
                email=email,
                name=name,
                picture=picture,
                provider=provider,
            )
            db.session.add(user)
            db.session.commit()
            print(f"🆕 新用戶註冊: {email} ({provider})")

        return user

    def to_dict(self):
        """轉換為字典"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "provider": self.provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_admin": self.is_admin,
        }


# ============================================
# 認證藍圖（Flask Blueprint）
# ============================================
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# OAuth 和 LoginManager 實例
oauth = OAuth()
login_manager = LoginManager()


def init_auth(app):
    """
    初始化認證系統

    在 app.py 中使用：
        from auth import init_auth
        init_auth(app.server)
    """
    # 設定 Flask
    app.secret_key = AuthConfig.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = AuthConfig.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = (
        AuthConfig.SQLALCHEMY_TRACK_MODIFICATIONS
    )

    # 確保資料庫目錄存在
    os.makedirs(AuthConfig.DB_DIR, exist_ok=True)

    # 初始化 SQLAlchemy
    db.init_app(app)

    # 建立資料表
    with app.app_context():
        db.create_all()
        print(f"✅ 資料庫已初始化: {AuthConfig.SQLALCHEMY_DATABASE_URI}")

    # 初始化 OAuth
    oauth.init_app(app)

    # 註冊 Google OAuth
    if AuthConfig.GOOGLE_CLIENT_ID and AuthConfig.GOOGLE_CLIENT_SECRET:
        oauth.register(
            name="google",
            client_id=AuthConfig.GOOGLE_CLIENT_ID,
            client_secret=AuthConfig.GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        print("✅ Google OAuth 已設定")
    else:
        print("⚠️  Google OAuth 未設定（缺少 GOOGLE_CLIENT_ID 或 GOOGLE_CLIENT_SECRET）")

    # 註冊 Facebook OAuth
    if AuthConfig.FACEBOOK_CLIENT_ID and AuthConfig.FACEBOOK_CLIENT_SECRET:
        oauth.register(
            name="facebook",
            client_id=AuthConfig.FACEBOOK_CLIENT_ID,
            client_secret=AuthConfig.FACEBOOK_CLIENT_SECRET,
            authorize_url="https://www.facebook.com/v18.0/dialog/oauth",
            access_token_url="https://graph.facebook.com/v18.0/oauth/access_token",
            api_base_url="https://graph.facebook.com/v18.0/",
            client_kwargs={"scope": "email public_profile"},
        )
        print("✅ Facebook OAuth 已設定")
    else:
        print(
            "⚠️  Facebook OAuth 未設定（缺少 FACEBOOK_CLIENT_ID 或 FACEBOOK_CLIENT_SECRET）"
        )

    # 初始化 Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login_page"
    login_manager.login_message = "請先登入"

    # 註冊認證路由
    app.register_blueprint(auth_bp)

    print("🔐 認證系統初始化完成")


@login_manager.user_loader
def load_user(user_id):
    """載入用戶（Flask-Login 需要）"""
    return User.query.get(int(user_id))


# ============================================
# 認證路由
# ============================================


@auth_bp.route("/login")
def login_page():
    """登入頁面"""
    if current_user.is_authenticated:
        return redirect(AuthConfig.LOGIN_REDIRECT_URL)

    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Beat Beta</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .login-card {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 400px;
                width: 100%;
            }
            .login-title { color: #333; margin-bottom: 10px; }
            .login-subtitle { color: #666; margin-bottom: 30px; }
            .btn-google {
                background: #fff;
                border: 2px solid #ddd;
                color: #333;
                padding: 12px 20px;
                border-radius: 10px;
                width: 100%;
                margin-bottom: 15px;
                transition: all 0.3s;
                text-decoration: none;
            }
            .btn-google:hover {
                background: #f8f9fa;
                border-color: #4285f4;
                box-shadow: 0 4px 12px rgba(66, 133, 244, 0.3);
            }
            /* Google 官方 SVG Logo */
            .google-icon {
                width: 20px;
                height: 20px;
                margin-right: 10px;
            }
            .btn-facebook {
                background: #1877f2;
                border: none;
                color: white;
                padding: 12px 20px;
                border-radius: 10px;
                width: 100%;
                transition: all 0.3s;
                text-decoration: none;
            }
            .btn-facebook:hover {
                background: #166fe5;
                color: white;
                box-shadow: 0 4px 12px rgba(24, 119, 242, 0.4);
            }
           
        </style>
    </head>
    <body>
        <div class="login-card text-center">
            <h2 class="login-title">Welcome to Beat Beta</h2>
            <p class="login-subtitle">請選擇登入方式</p>
            
            <a href="/auth/google" class="btn btn-google d-flex align-items-center justify-content-center">
                <svg class="google-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                使用 Google 帳號登入
            </a>
            
            <a href="/auth/facebook" class="btn btn-facebook d-flex align-items-center justify-content-center">
                <i class="fab fa-facebook-f me-2"></i>
                使用 Facebook 帳號登入
            </a>
            
            <hr class="my-4">
            <p class="text-muted small">
                登入即表示您同意我們的服務條款與隱私權政策
            </p>
        </div>
    </body>
    </html>
    """
    return html


@auth_bp.route("/google")
def google_login():
    """Google 登入"""
    if "google" not in oauth._clients:
        return "Google OAuth 未設定", 400

    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    """Google 登入回調"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get("userinfo")

        if user_info:
            user = User.get_or_create(
                oauth_id=f"google_{user_info['sub']}",
                email=user_info.get("email"),
                name=user_info.get("name"),
                picture=user_info.get("picture"),
                provider="google",
            )
            login_user(user)
            print(f"✅ Google 登入成功: {user.email}")
            return redirect(AuthConfig.LOGIN_REDIRECT_URL)

        return "無法取得用戶資訊", 400

    except Exception as e:
        print(f"❌ Google 登入失敗: {e}")
        return f"登入失敗: {str(e)}", 400


@auth_bp.route("/facebook")
def facebook_login():
    """Facebook 登入"""
    if "facebook" not in oauth._clients:
        return "Facebook OAuth 未設定", 400

    redirect_uri = url_for("auth.facebook_callback", _external=True)
    return oauth.facebook.authorize_redirect(redirect_uri)


@auth_bp.route("/facebook/callback")
def facebook_callback():
    """Facebook 登入回調"""
    try:
        token = oauth.facebook.authorize_access_token()
        resp = oauth.facebook.get("me?fields=id,name,email,picture")
        user_info = resp.json()

        if user_info:
            picture_url = user_info.get("picture", {}).get("data", {}).get("url")

            user = User.get_or_create(
                oauth_id=f"facebook_{user_info['id']}",
                email=user_info.get("email"),
                name=user_info.get("name"),
                picture=picture_url,
                provider="facebook",
            )
            login_user(user)
            print(f"✅ Facebook 登入成功: {user.email}")
            return redirect(AuthConfig.LOGIN_REDIRECT_URL)

        return "無法取得用戶資訊", 400

    except Exception as e:
        print(f"❌ Facebook 登入失敗: {e}")
        return f"登入失敗: {str(e)}", 400


@auth_bp.route("/logout")
def logout():
    """登出"""
    logout_user()
    return redirect("/auth/login")


@auth_bp.route("/user")
def user_info_api():
    """取得當前用戶資訊（API）"""
    if current_user.is_authenticated:
        return current_user.to_dict()
    return {"error": "未登入"}, 401


# ============================================
# 管理功能（可選）
# ============================================


@auth_bp.route("/admin/users")
@login_required
def admin_users():
    """列出所有用戶（僅管理員）"""
    if not current_user.is_admin:
        return {"error": "權限不足"}, 403

    users = User.query.order_by(User.created_at.desc()).all()
    return {"total": len(users), "users": [u.to_dict() for u in users]}


# ============================================
# Dash 整合工具
# ============================================


def get_current_user():
    """取得當前登入用戶（在 Dash callback 中使用）"""
    if current_user.is_authenticated:
        return current_user.to_dict()
    return None


def require_login(func):
    """
    裝飾器：要求登入

    使用方式：
        @callback(...)
        @require_login
        def my_callback(...):
            ...
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return None
        return func(*args, **kwargs)

    return decorated_function


def get_user_count():
    """取得用戶總數"""
    return User.query.count()


def get_recent_users(limit=10):
    """取得最近註冊的用戶"""
    users = User.query.order_by(User.created_at.desc()).limit(limit).all()
    return [u.to_dict() for u in users]
