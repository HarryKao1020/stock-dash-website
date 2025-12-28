"""
用戶介面元件 - 用於 Dash 顯示登入狀態
"""

from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from flask_login import current_user


def create_user_badge():
    """
    建立用戶狀態徽章
    顯示在導航列上
    """
    return html.Div(
        id="user-badge-container", className="ms-auto d-flex align-items-center"
    )


def create_user_dropdown():
    """
    建立用戶下拉選單
    包含用戶資訊和登出按鈕
    """
    return dbc.DropdownMenu(
        id="user-dropdown",
        label="",
        children=[],
        nav=True,
        in_navbar=True,
        align_end=True,
        className="user-dropdown",
    )


def get_user_badge_content():
    """
    取得用戶徽章內容
    根據登入狀態返回不同內容
    """
    if current_user.is_authenticated:
        # 已登入 - 顯示用戶頭像和名稱
        return html.Div(
            [
                # 用戶頭像
                (
                    html.Img(
                        src=current_user.picture or "/assets/default-avatar.png",
                        className="rounded-circle me-2",
                        style={"width": "32px", "height": "32px", "objectFit": "cover"},
                    )
                    if current_user.picture
                    else html.I(
                        className="fas fa-user-circle me-2",
                        style={"fontSize": "24px", "color": "#6c757d"},
                    )
                ),
                # 用戶名稱
                html.Span(
                    current_user.name or current_user.email,
                    className="me-2 d-none d-md-inline",
                    style={"color": "#333", "fontSize": "14px"},
                ),
                # 登出按鈕
                dbc.Button(
                    [html.I(className="fas fa-sign-out-alt me-1"), "登出"],
                    href="/auth/logout",
                    color="outline-secondary",
                    size="sm",
                    className="ms-2",
                ),
            ],
            className="d-flex align-items-center",
        )
    else:
        # 未登入 - 顯示登入按鈕
        return html.Div(
            [
                dbc.Button(
                    [html.I(className="fas fa-sign-in-alt me-1"), "登入"],
                    href="/auth/login",
                    color="primary",
                    size="sm",
                )
            ]
        )


def create_login_required_modal():
    """
    建立需要登入的提示 Modal
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("需要登入"), close_button=True),
            dbc.ModalBody(
                [
                    html.P("此功能需要登入才能使用。"),
                    html.P("請使用 Google 帳號登入。"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("前往登入", href="/auth/login", color="primary"),
                    dbc.Button(
                        "取消",
                        id="close-login-modal",
                        className="ms-2",
                        color="secondary",
                    ),
                ]
            ),
        ],
        id="login-required-modal",
        is_open=False,
        centered=True,
    )


# ============================================
# Dash Callbacks
# ============================================


def register_user_callbacks(app):
    """
    註冊用戶相關的 callbacks

    在 app.py 中使用：
        from user_components import register_user_callbacks
        register_user_callbacks(app)
    """

    @app.callback(
        Output("user-badge-container", "children"),
        Input("url", "pathname"),  # 頁面切換時更新
        prevent_initial_call=False,
    )
    def update_user_badge(pathname):
        """更新用戶徽章"""
        return get_user_badge_content()

    @app.callback(
        Output("login-required-modal", "is_open"),
        [Input("close-login-modal", "n_clicks")],
        [State("login-required-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_login_modal(n_clicks, is_open):
        """關閉登入提示 Modal"""
        if n_clicks:
            return False
        return is_open


# ============================================
# CSS 樣式
# ============================================

USER_STYLES = """
/* 用戶徽章樣式 */
.user-dropdown .dropdown-toggle::after {
    display: none;
}

.user-dropdown .dropdown-menu {
    min-width: 200px;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.user-info-header {
    padding: 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px 10px 0 0;
}

.user-avatar {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    border: 3px solid rgba(255,255,255,0.3);
}

/* 登入按鈕動畫 */
.btn-login {
    transition: all 0.3s ease;
}

.btn-login:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* 登入頁面背景 */
.login-page {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}
"""
