import dash
from dash import Dash, html, dcc
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
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# ✅ 為 Gunicorn 提供 WSGI 入口點（必須放在條件判斷外面）
server = app.server

# 側邊導航列
sidebar = dbc.Nav(
    [
        dbc.NavLink(
            [html.I(className="fas fa-chart-bar me-2"), html.Span("首頁/世界指數")],
            href="/",
            active="exact",
        ),
        dbc.NavLink(
            [html.I(className="fas fa-chart-bar me-2"), html.Span("即時盤勢")],
            href="/realtime-market",
            active="exact",
        ),
        dbc.NavLink(
            [html.I(className="fas fa-chart-line me-2"), html.Span("K線圖")],
            href="/kline",
            active="exact",
        ),
        dbc.NavLink(
            [html.I(className="fas fa-th me-2"), html.Span("族群區塊圖")],
            href="/treemap",
            active="exact",
        ),
        dbc.NavLink(
            [
                html.I(className="fas fa-chart-line me-2"),
                html.Span("融資卷餘額/維持率"),
            ],
            href="/margin-balance",
            active="exact",
        ),
        dbc.NavLink(
            [
                html.I(className="fas fa-trophy me-2"),
                html.Span("市值排行"),
            ],
            href="/market-value-ranking",
            active="exact",
        ),
        dbc.NavLink(
            [
                html.I(className="fas fa-money-bill-wave me-2"),
                html.Span("金流排行"),
            ],
            href="/money-flow",
            active="exact",
        ),
    ],
    vertical=True,
    pills=True,
    className="bg-light sidebar",
)

# 主要布局
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                # 側邊欄
                dbc.Col(sidebar, width=2, className="bg-light min-vh-100"),
                # 主要內容區
                dbc.Col(dash.page_container, width=10, className="p-4"),
            ]
        )
    ],
    fluid=True,
)

# 本地開發時直接執行
if __name__ == "__main__":
    # 判斷環境決定 debug 模式
    debug_mode = os.environ.get("DEBUG", "true").lower() == "true"
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
