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

# 強制清除舊快取（第一次執行後可以註解掉）
print("🔄 清除舊快取...")
finlab_data.refresh()
print("✅ 快取已清除，重新下載資料中...")

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


# 本地啟動server
if __name__ == "__main__":
    app.run(debug=True)


# 部署到 Render
# server = app.server  # 給 gunicorn 使用
# if __name__ == "__main__":
#     app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
