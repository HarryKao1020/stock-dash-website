import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path

# 將專案根目錄加入 Python path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# ================
# 👇 加入診斷代碼
print("=" * 60)
print(f"🔍 home.py 診斷資訊")
print(f"📁 PROJECT_DIR: {PROJECT_DIR.absolute()}")
print(f"📁 home.py 位置: {Path(__file__).absolute()}")
print("=" * 60)

from finlab_data import finlab_data

# 👇 測試資料日期
print("🧪 測試 finlab_data 在 home.py 中的資料:")
test_close = finlab_data.world_index_close
print(f"   資料日期範圍: {test_close.index.min()} ~ {test_close.index.max()}")
if "^TWII" in test_close.columns:
    tw_data = test_close["^TWII"].dropna()
    print(f"   台灣指數最新日期: {tw_data.index.max()}")
    print(f"   台灣指數最新值: {tw_data.iloc[-1]}")
print("=" * 60)

# ================

dash.register_page(__name__, path="/", name="首頁")

# 國際指數資訊
WORLD_INDICES = {
    "^TWII": {"name": "台灣加權指數", "color": "#ef5350"},
    "^GSPC": {"name": "S&P 500", "color": "#5c6bc0"},
    "^DJI": {"name": "道瓊工業指數", "color": "#26a69a"},
    "^IXIC": {"name": "NASDAQ", "color": "#ab47bc"},
    "^N225": {"name": "日經225", "color": "#ff7043"},
    "^KS11": {"name": "韓國綜合指數", "color": "#66bb6a"},
}


def create_world_index_candlestick(index_code, days=120):
    """
    創建國際指數 K 線圖(含 MA20, MA60, MA120)
    """
    try:
        df = finlab_data.get_world_index_data(index_code, days=days)
        index_info = WORLD_INDICES.get(
            index_code, {"name": index_code, "color": "#ef5350"}
        )

        # 🆕 將日期索引轉換為字串格式（用於 category 類型 x 軸）
        df.index = df.index.strftime("%Y-%m-%d")

        # 計算每日漲跌幅
        df["change_pct"] = ((df["close"] - df["open"]) / df["open"] * 100).round(2)
        df["change"] = (df["close"] - df["open"]).round(2)

        # 創建單一圖表
        fig = go.Figure()

        # K線圖 - 加入自訂 hover 資訊
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="K線",
                increasing_line_color="#ef5350",
                decreasing_line_color="#26a69a",
                hovertext=[
                    f"日期: {date}<br>"
                    f"開: {row['open']:.2f}<br>"
                    f"高: {row['high']:.2f}<br>"
                    f"低: {row['low']:.2f}<br>"
                    f"收: {row['close']:.2f}<br>"
                    f"<b>漲跌: {row['change']:+.2f} ({row['change_pct']:+.2f}%)</b>"
                    for date, row in df.iterrows()
                ],
                hoverinfo="text",
            )
        )

        # 20日均線
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["ma20"],
                mode="lines",
                name="MA20",
                line=dict(color="#fc0707", width=1.5),
                hovertemplate="MA20: %{y:.2f}<extra></extra>",
            )
        )

        # 60日均線
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["ma60"],
                mode="lines",
                name="MA60",
                line=dict(color="#ff9800", width=1.5),
                hovertemplate="MA60: %{y:.2f}<extra></extra>",
            )
        )

        # 120日均線
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["ma120"],
                mode="lines",
                name="MA120",
                line=dict(color="#2196f3", width=1.5),
                hovertemplate="MA120: %{y:.2f}<extra></extra>",
            )
        )

        fig.update_layout(
            title=f'{index_info["name"]} K線圖',
            height=450,
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            margin=dict(l=50, r=20, t=50, b=50),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            yaxis=dict(hoverformat=".2f"),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial",
            ),
        )

        # 🆕 使用 category 類型來自動移除空白日期
        fig.update_xaxes(
            type="category",  # 關鍵：使用 category 類型
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
        )
        fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")

        return fig

    except Exception as e:
        # 錯誤處理...
        fig = go.Figure()
        fig.add_annotation(
            text=f"載入失敗: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="red"),
        )
        fig.update_layout(height=450)
        return fig


def create_world_indices_comparison(days=365):
    """創建國際指數漲跌幅比較圖"""
    try:
        fig = go.Figure()

        for index_code, info in WORLD_INDICES.items():
            try:
                df = finlab_data.get_world_index_data(index_code, days=days)

                # 🆕 將日期索引轉為字串
                df.index = df.index.strftime("%Y-%m-%d")

                # 計算相對於第一天的漲跌幅 (%)
                returns = ((df["close"] / df["close"].iloc[0]) - 1) * 100

                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=returns,
                        mode="lines",
                        name=info["name"],
                        line=dict(width=2, color=info["color"]),
                    )
                )
            except:
                continue

        fig.update_layout(
            title=f"國際指數漲跌幅比較 (近{days}天)",
            xaxis_title="日期",
            yaxis_title="漲跌幅 (%)",
            hovermode="x unified",
            height=400,
            margin=dict(l=50, r=20, t=50, b=50),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

        # 🆕 使用 category 類型
        fig.update_xaxes(
            type="category", showgrid=True, gridcolor="rgba(128,128,128,0.2)"
        )
        fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")

        return fig

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(
            text=f"載入失敗: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="red"),
        )
        fig.update_layout(height=400)
        return fig


# 頁面布局
layout = dbc.Container(
    [
        # 標題區
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H1(
                                    "🚀 歡迎來到老高的操盤小天地",
                                    className="text-center mb-3",
                                    style={"color": "#2c3e50", "font-weight": "bold"},
                                ),
                                html.P(
                                    "主要是將有用的數據整理成圖表,方便在同一個網站閱讀",
                                    className="text-center text-muted mb-4",
                                    style={"font-size": "1.2rem"},
                                ),
                                html.Hr(
                                    style={
                                        "border-color": "#00a896",
                                        "border-width": "2px",
                                    }
                                ),
                            ],
                            className="my-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # 特色功能卡片
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dcc.Link(
                                    dbc.CardBody(
                                        [
                                            html.I(
                                                className="fas fa-chart-line fa-3x text-primary mb-3"
                                            ),
                                            html.H5("即時盤勢", className="card-title"),
                                            html.P(
                                                "追蹤大盤與個股走勢",
                                                className="card-text text-muted",
                                            ),
                                        ],
                                        className="text-center",
                                    ),
                                    href="/market-status",  # 你的頁面路徑
                                    style={
                                        "textDecoration": "none",
                                        "color": "inherit",
                                    },
                                )
                            ],
                            className="shadow-sm h-100",
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dcc.Link(
                                    dbc.CardBody(
                                        [
                                            html.I(
                                                className="fas fa-chart-bar fa-3x text-success mb-3"
                                            ),
                                            html.H5("K線圖", className="card-title"),
                                            html.P(
                                                "K線圖與技術指標",
                                                className="card-text text-muted",
                                            ),
                                        ],
                                        className="text-center",
                                    ),
                                    href="/kline",  # 你的頁面路徑
                                    style={
                                        "textDecoration": "none",
                                        "color": "inherit",
                                    },
                                )
                            ],
                            className="shadow-sm h-100",
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dcc.Link(
                                    dbc.CardBody(
                                        [
                                            html.I(
                                                className="fas fa-th fa-3x text-warning mb-3"
                                            ),
                                            html.H5("產業分類", className="card-title"),
                                            html.P(
                                                "視覺化呈現產業表現",
                                                className="card-text text-muted",
                                            ),
                                        ],
                                        className="text-center",
                                    ),
                                    href="/treemap",  # 你的頁面路徑
                                    style={
                                        "textDecoration": "none",
                                        "color": "inherit",
                                    },
                                )
                            ],
                            className="shadow-sm h-100",
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.I(
                                            className="fas fa-balance-scale fa-3x text-danger mb-3"
                                        ),
                                        html.H5("籌碼分析", className="card-title"),
                                        html.P(
                                            "融資融券變化追蹤",
                                            className="card-text text-muted",
                                        ),
                                    ],
                                    className="text-center",
                                )
                            ],
                            className="shadow-sm h-100",
                        )
                    ],
                    width=3,
                ),
            ],
            className="mb-5",
        ),
        # 國際指數比較圖
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            figure=create_world_indices_comparison(),
                                            config={"displayModeBar": False},
                                        )
                                    ]
                                )
                            ],
                            className="shadow-sm mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # 統一控制 K 線圖顯示天數的 Slider
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.Div(
                                            [
                                                html.H5(
                                                    "📊 K線圖顯示天數控制",
                                                    style={
                                                        "font-weight": "bold",
                                                        "color": "#2c3e50",
                                                        "margin-bottom": "15px",
                                                    },
                                                ),
                                                dcc.Slider(
                                                    id="global-days-slider",
                                                    min=120,
                                                    max=365,
                                                    step=5,
                                                    value=120,
                                                    marks={
                                                        120: "120天",
                                                        180: "180天",
                                                        240: "240天",
                                                        300: "300天",
                                                        365: "365天",
                                                    },
                                                    tooltip={
                                                        "placement": "bottom",
                                                        "always_visible": True,
                                                    },
                                                ),
                                            ]
                                        )
                                    ]
                                )
                            ],
                            className="shadow-sm mb-4",
                            style={"background-color": "#f8f9fa"},
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # 國際指數 K 線圖 - 第一排
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            id="graph-twii",
                                            figure=create_world_index_candlestick(
                                                "^TWII", days=120
                                            ),
                                            config={"displayModeBar": False},
                                        )
                                    ]
                                )
                            ],
                            className="shadow-sm mb-4",
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            id="graph-gspc",
                                            figure=create_world_index_candlestick(
                                                "^GSPC", days=120
                                            ),
                                            config={"displayModeBar": False},
                                        )
                                    ]
                                )
                            ],
                            className="shadow-sm mb-4",
                        )
                    ],
                    width=6,
                ),
            ]
        ),
        # 國際指數 K 線圖 - 第二排
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            id="graph-dji",
                                            figure=create_world_index_candlestick(
                                                "^DJI", days=120
                                            ),
                                            config={"displayModeBar": False},
                                        )
                                    ]
                                )
                            ],
                            className="shadow-sm mb-4",
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            id="graph-ixic",
                                            figure=create_world_index_candlestick(
                                                "^IXIC", days=120
                                            ),
                                            config={"displayModeBar": False},
                                        )
                                    ]
                                )
                            ],
                            className="shadow-sm mb-4",
                        )
                    ],
                    width=6,
                ),
            ]
        ),
        # 國際指數 K 線圖 - 第三排
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            id="graph-n225",
                                            figure=create_world_index_candlestick(
                                                "^N225", days=120
                                            ),
                                            config={"displayModeBar": False},
                                        )
                                    ]
                                )
                            ],
                            className="shadow-sm mb-4",
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            id="graph-ks11",
                                            figure=create_world_index_candlestick(
                                                "^KS11", days=120
                                            ),
                                            config={"displayModeBar": False},
                                        )
                                    ]
                                )
                            ],
                            className="shadow-sm mb-4",
                        )
                    ],
                    width=6,
                ),
            ]
        ),
        # 底部說明
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Alert(
                            [
                                html.I(className="fas fa-info-circle me-2"),
                                "提示:以上為 FinLab 真實數據,包含 60日均線(橘色) 與 120日均線(藍色)。",
                            ],
                            color="info",
                            className="text-center",
                        )
                    ],
                    width=12,
                )
            ]
        ),
    ],
    fluid=True,
    className="p-4",
)


# 統一 Callback: 一個 slider 控制所有圖表
@callback(
    [
        Output("graph-twii", "figure"),
        Output("graph-gspc", "figure"),
        Output("graph-dji", "figure"),
        Output("graph-ixic", "figure"),
        Output("graph-n225", "figure"),
        Output("graph-ks11", "figure"),
    ],
    Input("global-days-slider", "value"),
)
def update_all_charts(days):
    """統一更新所有 K 線圖"""
    return (
        create_world_index_candlestick("^TWII", days=days),
        create_world_index_candlestick("^GSPC", days=days),
        create_world_index_candlestick("^DJI", days=days),
        create_world_index_candlestick("^IXIC", days=days),
        create_world_index_candlestick("^N225", days=days),
        create_world_index_candlestick("^KS11", days=days),
    )
