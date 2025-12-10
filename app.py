import dash
from dash import Dash, html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import os


# 👇 加入這段
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from finlab_data import finlab_data

# 生產環境不要每次啟動都清除快取（浪費時間和 API 額度）
# 如果需要手動清除，可以刪除 cache 目錄內的檔案
print("🚀 啟動中，使用現有快取...")

# 測試資料
print("🧪 app.py 中的資料測試:")
test_close = finlab_data.world_index_close
print(f"   資料日期範圍: {test_close.index.min()} ~ {test_close.index.max()}")

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

# ✅ 為 Gunicorn 提供 WSGI 入口點（必須放在條件判斷外面）
server = app.server

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

# 桌面版側邊導航列
sidebar_desktop = html.Div(
    [
        # Logo/標題區
        html.Div(
            [
                html.H5("📊 操你的飆股", className="text-primary mb-0 fw-bold"),
            ],
            className="sidebar-header p-3 border-bottom",
        ),
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
            className="flex-column pt-2",
        ),
    ],
    className="sidebar-desktop",
    id="sidebar-desktop",
)

# 手機版頂部導航列
navbar_mobile = dbc.Navbar(
    dbc.Container(
        [
            # Logo
            html.A(
                html.Span("📊 操盤小天地", className="navbar-brand-text fw-bold"),
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
                html.H5("📊 操盤小天地", className="text-primary fw-bold"),
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
        # 手機版導航列
        navbar_mobile,
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
                                className="main-content p-3 p-lg-4",
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
        ),
    ],
    className="app-wrapper",
)


# Callback: 切換手機版側邊選單
@callback(
    Output("sidebar-mobile", "is_open"),
    [Input("navbar-toggler", "n_clicks")]
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
    if trigger_id == "navbar-toggler":
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
