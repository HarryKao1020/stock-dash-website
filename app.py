import dash
from dash import Dash, html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import os
from data.finlab_data import finlab_data
from auth import init_auth
from flask import session, redirect, request, jsonify
from flask_login import current_user
import sys
from pathlib import Path
import time

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

# 使用 lazy loading + Parquet 快取
# 快取更新由 cron job 排程執行（scripts/update_cache.py）
print("🚀 啟動中，使用現有快取（Parquet 格式）...")


# 初始化 Dash app,使用 Bootstrap 主題
app = Dash(
    __name__,
    use_pages=True,  # 啟用多頁面功能
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)

# 存儲深色模式狀態
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            const isDark = document.body.classList.toggle('dark-mode');
            localStorage.setItem('darkMode', isDark ? 'true' : 'false');
            return isDark;
        }
        // 初始化時從 localStorage 讀取
        const savedMode = localStorage.getItem('darkMode');
        if (savedMode === 'true') {
            document.body.classList.add('dark-mode');
            return true;
        }
        return false;
    }
    """,
    Output("dark-mode-state", "data"),
    Input("dark-mode-toggle", "n_clicks"),
    prevent_initial_call=False,
)

# ✅ 為 Gunicorn 提供 WSGI 入口點（必須放在條件判斷外面）
server = app.server
init_auth(server)


# ==================== 預熱 API 端點 ====================
@server.route("/api/warmup", methods=["GET"])
def warmup_data():
    """
    預熱端點 - 預先載入所有常用資料到記憶體

    使用方式:
    - 手動觸發: curl http://localhost:8050/api/warmup
    - cron 排程: 0 8 * * 1-5 curl http://localhost:8050/api/warmup
    """
    start_time = time.time()
    results = {"status": "success", "loaded": [], "errors": []}

    try:
        # 1. 預載 FinLab 常用資料
        print("🔥 預熱開始 - 載入 FinLab 資料...")
        finlab_datasets = [
            ("收盤價", lambda: finlab_data.close),
            ("成交量", lambda: finlab_data.volume),
            ("成交金額", lambda: finlab_data.amount),
            ("世界指數收盤價", lambda: finlab_data.world_index_close),
            ("融資維持率", lambda: finlab_data.margin_maintenance_ratio),
            ("月營收", lambda: finlab_data.monthly_revenue),
            ("營收YoY", lambda: finlab_data.revenue_yoy),
        ]

        for name, loader in finlab_datasets:
            try:
                data = loader()
                results["loaded"].append(f"FinLab:{name} ({len(data)} records)")
            except Exception as e:
                results["errors"].append(f"FinLab:{name} - {str(e)}")

        # 2. 預載 Shioaji 資料(如果已登入)
        try:
            from data.shioaji_data import get_cached_or_fetch
            from auth import get_shioaji_api

            api = get_shioaji_api()
            if api:
                print("🔥 預熱 Shioaji 資料...")
                tse_df, otc_df = get_cached_or_fetch(api)
                results["loaded"].append(f"Shioaji:TSE ({len(tse_df)} days)")
                results["loaded"].append(f"Shioaji:OTC ({len(otc_df)} days)")
            else:
                results["errors"].append("Shioaji:API 未登入")
        except Exception as e:
            results["errors"].append(f"Shioaji - {str(e)}")

        elapsed = time.time() - start_time
        results["elapsed_seconds"] = round(elapsed, 2)

        print(f"✅ 預熱完成! 耗時: {elapsed:.2f} 秒")
        print(f"   成功載入: {len(results['loaded'])} 項")
        print(f"   錯誤: {len(results['errors'])} 項")

        return jsonify(results), 200

    except Exception as e:
        results["status"] = "error"
        results["message"] = str(e)
        return jsonify(results), 500


# 頁面登入保護
@server.before_request
def require_login():
    """檢查是否需要登入"""
    # 不需要登入的路徑
    public_paths = [
        "/auth/",  # 認證相關路由
        "/_dash-",  # Dash 內部請求
        "/assets/",  # 靜態資源
        "/_reload-hash",  # Dash hot reload
    ]

    # 檢查是否為公開路徑
    for path in public_paths:
        if request.path.startswith(path):
            return None

    # 檢查環境變數是否啟用登入限制
    login_required = os.environ.get("LOGIN_REQUIRED", "false").lower() == "true"

    if login_required and not current_user.is_authenticated:
        # 未登入則導向登入頁
        return redirect("/auth/login")


# 導航連結資料
nav_links = [
    {"icon": "fa-home", "text": "首頁/世界指數", "href": "/"},
    {"icon": "fa-chart-line", "text": "即時盤勢", "href": "/realtime-market"},
    {"icon": "fa-chart-simple", "text": "K線圖", "href": "/kline"},
    {"icon": "fa-th-large", "text": "族群區塊圖", "href": "/treemap"},
    {"icon": "fa-coins", "text": "融資卷餘額/維持率", "href": "/margin-balance"},
    {"icon": "fa-trophy", "text": "市值排行", "href": "/market-value-ranking"},
    {"icon": "fa-sack-dollar", "text": "金流排行", "href": "/money-flow"},
    {"icon": "fa-chart-bar", "text": "營收排行", "href": "/rev-rank"},
]

# 頂部導航欄 (所有裝置共用)
top_navbar = dbc.Navbar(
    dbc.Container(
        [
            # 左側區域 (手機版漢堡選單 + Logo)
            html.Div(
                [
                    # 手機版漢堡選單按鈕 (只在 lg 以下顯示)
                    dbc.Button(
                        html.I(className="fas fa-bars fa-lg", id="mobile-menu-icon"),
                        id="mobile-menu-toggler",
                        className="d-lg-none border-0 p-2 me-2",
                        style={"background": "transparent"},
                        n_clicks=0,
                    ),
                    # Logo
                    html.A(
                        html.Img(
                            src="/assets/betabeta.png",
                            style={
                                "height": "40px",
                                "maxWidth": "200px",
                                "objectFit": "contain",
                            },
                        ),
                        href="/",
                        className="navbar-brand d-flex align-items-center",
                    ),
                ],
                className="d-flex align-items-center",
            ),
            # 右側控制區
            html.Div(
                [
                    # 深色模式切換按鈕
                    dbc.Button(
                        html.I(id="dark-mode-icon", className="fas fa-moon"),
                        id="dark-mode-toggle",
                        color="link",
                        className="dark-mode-toggle me-3",
                        n_clicks=0,
                    ),
                    # 用戶頭像選單
                    html.Div(
                        id="user-menu-container",
                        className="d-flex align-items-center",
                    ),
                ],
                className="d-flex align-items-center",
            ),
        ],
        fluid=True,
        className="px-3",
    ),
    id="top-navbar",
    color="dark",
    dark=True,
    className="top-navbar fixed-top",
    style={"height": "60px"},
)

# 桌面版側邊導航列
sidebar_desktop = html.Div(
    [
        # 導航連結
        dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.I(className=f"fas {link['icon']} me-2"),
                        html.Span(link["text"]),
                    ],
                    href=link["href"],
                    active="exact",
                    className="sidebar-link",
                )
                for link in nav_links
            ],
            vertical=True,
            pills=True,
            className="flex-column pt-3",
        ),
    ],
    className="sidebar-desktop",
    id="sidebar-desktop",
    style={"marginTop": "0px"},  # 為頂部導航欄留空間
)

# 手機版頂部導航列
navbar_mobile = dbc.Navbar(
    dbc.Container(
        [
            # Logo
            html.A(
                html.Img(
                    src="/assets/betabeta.png",
                    style={
                        "height": "35px",
                        "maxWidth": "180px",
                        "objectFit": "contain",
                    },
                ),
                href="/",
                className="navbar-brand",
            ),
            # 漢堡選單按鈕
            dbc.Button(
                html.I(className="fas fa-bars fa-lg"),
                id="navbar-toggler",
                className="navbar-toggler border-0 p-2",
                n_clicks=0,
            ),
        ],
        fluid=True,
    ),
    color="primary",
    dark=True,
    className="d-lg-none navbar-mobile",
    sticky="top",
)

# 手機版側邊抽屜選單
sidebar_mobile = dbc.Offcanvas(
    [
        html.Div(
            [
                html.Div(
                    html.Img(
                        src="/assets/betabeta.png",
                        style={
                            "height": "40px",
                            "maxWidth": "200px",
                            "objectFit": "contain",
                        },
                    ),
                    className="d-flex align-items-center",
                ),
                html.Hr(),
            ],
            className="mb-3",
        ),
        dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.I(className=f"fas {link['icon']} me-3 fs-5"),
                        html.Span(link["text"], className="fs-6"),
                    ],
                    href=link["href"],
                    active="exact",
                    className="mobile-nav-link py-3 px-3 rounded mb-1",
                    id=f"mobile-link-{i}",
                )
                for i, link in enumerate(nav_links)
            ],
            vertical=True,
            pills=True,
        ),
    ],
    id="sidebar-mobile",
    title="",
    is_open=False,
    placement="start",
    className="offcanvas-mobile",
    style={"width": "280px"},
)

# 主要布局
app.layout = html.Div(
    [
        # 深色模式狀態存儲
        dcc.Store(id="dark-mode-state", storage_type="local"),
        # 頂部導航欄
        top_navbar,
        # 手機版導航列 (隱藏,改用頂部導航欄)
        # navbar_mobile,
        # 手機版側邊抽屜
        sidebar_mobile,
        # 主要內容區
        html.Div(
            [
                dbc.Row(
                    [
                        # 桌面版側邊欄
                        dbc.Col(
                            sidebar_desktop,
                            lg=2,
                            className="sidebar-col d-none d-lg-block p-0",
                        ),
                        # 主要內容區
                        dbc.Col(
                            html.Div(
                                dash.page_container,
                                className="main-content p-2 p-lg-4",
                            ),
                            xs=12,
                            lg=10,
                            className="content-col",
                        ),
                    ],
                    className="g-0",
                ),
            ],
            className="main-container",
            style={"marginTop": "40px"},  # 為頂部導航欄留空間
        ),
    ],
    className="app-wrapper",
)


# Callback: 更新用戶選單
@callback(
    Output("user-menu-container", "children"),
    Input("dark-mode-state", "data"),
    prevent_initial_call=False,
)
def update_user_menu(_):
    """更新用戶選單顯示"""
    if current_user.is_authenticated:
        # 已登入 - 顯示用戶頭像和下拉選單
        return dbc.DropdownMenu(
            [
                dbc.DropdownMenuItem(
                    [
                        html.I(className="fas fa-cog me-2"),
                        "Settings",
                    ],
                    href="#",
                    disabled=True,  # 暫時禁用
                ),
                dbc.DropdownMenuItem(divider=True),
                dbc.DropdownMenuItem(
                    html.A(
                        [
                            html.I(className="fas fa-sign-out-alt me-2"),
                            "Logout",
                        ],
                        href="/auth/logout",
                        style={"textDecoration": "none", "color": "inherit"},
                    ),
                ),
            ],
            label=html.Div(
                [
                    html.Img(
                        src=current_user.picture or "https://via.placeholder.com/40",
                        className="rounded-circle user-avatar-container",
                        style={
                            "width": "40px",
                            "height": "40px",
                            "objectFit": "cover",
                        },
                    ),
                ],
                className="d-inline-block",
            ),
            nav=True,
            in_navbar=True,
            align_end=True,
            className="user-dropdown",
            toggle_style={
                "background": "transparent",
                "border": "none",
                "padding": "0",
            },
        )
    else:
        # 未登入 - 顯示登入按鈕
        return html.A(
            dbc.Button(
                [html.I(className="fas fa-sign-in-alt me-2"), "登入"],
                color="primary",
                size="sm",
            ),
            href="/auth/login",
            style={"textDecoration": "none"},
        )


# Callback: 更新深色模式圖標和導航欄樣式
@callback(
    [
        Output("dark-mode-icon", "className"),
        Output("top-navbar", "color"),
        Output("top-navbar", "className"),
        Output("mobile-menu-icon", "style"),
        Output("dark-mode-toggle", "style"),
    ],
    Input("dark-mode-state", "data"),
    prevent_initial_call=False,
)
def update_dark_mode_ui(is_dark):
    """根據深色模式狀態更新圖標和導航欄樣式"""
    if is_dark:
        # 深色模式 - 使用深色導航欄
        return (
            "fas fa-sun",  # 圖標變成太陽
            "dark",  # 保持深色背景
            "top-navbar fixed-top navbar-dark-mode",  # 添加深色模式 class
            {"color": "#f5f5f5"},  # 漢堡選單圖標顏色
            {"color": "#f5f5f5"},  # 深色模式按鈕顏色
        )
    else:
        # 淺色模式 - 使用淺色導航欄
        return (
            "fas fa-moon",  # 圖標變成月亮
            "light",  # 淺色背景
            "top-navbar fixed-top navbar-light-mode",  # 添加淺色模式 class
            {"color": "#333"},  # 漢堡選單圖標顏色
            {"color": "#333"},  # 深色模式按鈕顏色
        )


# Callback: 切換手機版側邊選單
@callback(
    Output("sidebar-mobile", "is_open"),
    [Input("mobile-menu-toggler", "n_clicks")]
    + [Input(f"mobile-link-{i}", "n_clicks") for i in range(len(nav_links))],
    [State("sidebar-mobile", "is_open")],
    prevent_initial_call=True,
)
def toggle_sidebar(toggler_clicks, *args):
    """切換手機版側邊選單"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return False

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # 如果是漢堡按鈕，切換開關
    if trigger_id == "mobile-menu-toggler":
        return not args[-1]  # args[-1] 是 is_open state

    # 如果是導航連結，關閉選單
    if trigger_id.startswith("mobile-link-"):
        return False

    return args[-1]


# 本地開發時直接執行
if __name__ == "__main__":
    # 判斷環境決定 debug 模式
    debug_mode = os.environ.get("DEBUG", "true").lower() == "true"
    port = int(os.environ.get("PORT", 8050))

    app.run(debug=debug_mode, host="0.0.0.0", port=port)
