import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
import os
from dotenv import load_dotenv
import requests
import shioaji as sj
from shioaji import TickFOPv1, Exchange
from shioaji import BidAskFOPv1, Exchange
from shioaji import BidAskSTKv1, Exchange

# 載入 .env 檔案
load_dotenv()

try:
    import shioaji as sj
    from data.shioaji_data_backup import get_cached_or_fetch

    # 改成這樣:
    api_key = os.getenv("API_KEY")
    secret_key = os.getenv("SECRET_KEY")
    api = sj.Shioaji(simulation=True)
    accounts = api.login(api_key, secret_key)
    USE_REAL_DATA = True  # 改成 True
    print("測試帳號 登入成功！")
    print(f"可用帳戶: {accounts}")

except:
    api = None
    USE_REAL_DATA = False
    print(f"登入失敗: {e}")


dash.register_page(__name__, path="/realtime-market-backup", name="即時盤勢")

# ====== 變數區==========
font_size = "1rem"
days_to_display = 60  # 處置股天數
# ====== 變數區==========


def create_index_chart_with_macd(df, title="加權指數"):
    """
    建立包含 K線、均線、成交量和 MACD 的圖表

    Args:
        df: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume', 'ma5', 'ma20', 'ma60', 'ma120', 'DIF', 'MACD', 'MACD_Hist']
        title: 圖表標題
    """
    # 建立子圖 (K線+均線, 成交量, MACD)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.5, 0.2, 0.3],
        subplot_titles=(f"{title} K線圖", "成交量", "MACD"),
    )

    # === 第一張圖: K線 + 均線 ===
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K線",
            increasing_line_color="#ef5350",
            decreasing_line_color="#26a69a",
        ),
        row=1,
        col=1,
    )

    # 加入均線
    ma_configs = [
        ("ma5", "MA5", "#9c27b0"),
        ("ma20", "MA20", "#ff9800"),
        ("ma60", "MA60", "#2196f3"),
        ("ma120", "MA120", "#4caf50"),
    ]

    for ma_col, ma_name, color in ma_configs:
        if ma_col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[ma_col],
                    name=ma_name,
                    line=dict(color=color, width=1.5),
                    mode="lines",
                ),
                row=1,
                col=1,
            )

    # === 第二張圖: 成交量 ===
    colors = [
        "#ef5350" if close >= open_ else "#26a69a"
        for close, open_ in zip(df["Close"], df["Open"])
    ]

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="成交量",
            marker_color=colors,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # === 第三張圖: MACD ===
    # DIF 線
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["DIF"], name="DIF", line=dict(color="#2196f3", width=1.5)
        ),
        row=3,
        col=1,
    )

    # MACD 線
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["MACD"], name="MACD", line=dict(color="#ff9800", width=1.5)
        ),
        row=3,
        col=1,
    )

    # MACD 柱狀體
    macd_colors = ["#ef5350" if val >= 0 else "#26a69a" for val in df["MACD_Hist"]]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["MACD_Hist"],
            name="MACD柱狀體",
            marker_color=macd_colors,
            showlegend=False,
        ),
        row=3,
        col=1,
    )

    # 0 軸線
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=3, col=1)

    # 更新布局
    fig.update_layout(
        height=600,  # 縮小高度以配合並排顯示
        title=dict(
            text=title,
            font=dict(size=16, color="navy"),  # 標題字體也縮小
            x=0.5,
            xanchor="center",
        ),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10),  # 圖例字體縮小
        ),
        template="plotly_white",
        margin=dict(l=40, r=20, t=60, b=40),  # 調整邊距
    )

    # 更新軸標籤
    fig.update_xaxes(title_text="日期", row=3, col=1)
    fig.update_yaxes(title_text="價格", row=1, col=1)
    fig.update_yaxes(title_text="成交量(億)", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)

    return fig


def create_stock_count_chart(count_series, title="股票數量", color="#ff6b6b"):
    """
    建立處置股或警示股數量柱狀圖

    Args:
        count_series: pd.Series，日期為索引，數量為值（已過濾週末）
        title: 圖表標題
        color: 柱狀圖顏色

    Returns:
        plotly figure
    """
    # 將日期索引轉換為字串格式（只保留日期部分）
    date_strings = count_series.index.strftime("%Y-%m-%d")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=date_strings,  # 使用格式化後的日期字串
            y=count_series.values,
            name=title,
            marker_color=color,
            text=count_series.values,
            textposition="outside",
            hovertemplate="<b>日期</b>: %{x}<br>"
            + "<b>數量</b>: %{y}<br>"
            + "<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=16, color="navy"),
            x=0.5,
            xanchor="center",
            y=0.95,  # 將標題往下移
            yanchor="top",
        ),
        xaxis_title="日期",
        yaxis_title="數量",
        height=400,
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=50, r=20, t=80, b=50),
        showlegend=False,
    )

    # 使用 type='category' 來自動移除沒有資料的日期
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)", type="category")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")

    return fig


def generate_ma_analysis(latest_data, index_name="加權指數"):
    """
    生成均線分析文字

    Args:
        latest_data: Series，包含最新一筆資料
        index_name: 指數名稱
    """
    close = latest_data["Close"]

    analyses = []

    # 5日均線
    if pd.notna(latest_data.get("ma5")):
        ma5 = latest_data["ma5"]
        if close > ma5:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "✅ 站上5日均線",
                            style={"color": "red", "fontWeight": "bold"},
                        ),
                        html.Span(f" (現價: {close:.2f}, 5日均價: {ma5:.0f})"),
                    ]
                )
            )
        else:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "❌ 低於5日均線",
                            style={"color": "green", "fontWeight": "bold"},
                        ),
                        html.Span(f" (現價: {close:.2f}, 5日均價: {ma5:.0f})"),
                    ]
                )
            )

    # 20日均線 (月線)
    if pd.notna(latest_data.get("ma20")):
        ma20 = latest_data["ma20"]
        if close > ma20:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "✅ 站上月均線",
                            style={"color": "red", "fontWeight": "bold"},
                        ),
                        html.Span(f" (現價: {close:.2f}, 20日均價: {ma20:.0f})"),
                    ]
                )
            )
        else:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "❌ 低於月均線",
                            style={"color": "green", "fontWeight": "bold"},
                        ),
                        html.Span(f" (現價: {close:.2f}, 20日均價: {ma20:.0f})"),
                    ]
                )
            )

    # 60日均線 (季線)
    if pd.notna(latest_data.get("ma60")):
        ma60 = latest_data["ma60"]
        if close > ma60:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "✅ 站上季均線",
                            style={"color": "red", "fontWeight": "bold"},
                        ),
                        html.Span(f" (現價: {close:.2f}, 60日均價: {ma60:.0f})"),
                    ]
                )
            )
        else:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "❌ 低於季均線",
                            style={"color": "green", "fontWeight": "bold"},
                        ),
                        html.Span(f" (現價: {close:.2f}, 60日均價: {ma60:.0f})"),
                    ]
                )
            )

    # 120日均線 (半年線)
    if pd.notna(latest_data.get("ma120")):
        ma120 = latest_data["ma120"]
        if close > ma120:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "✅ 站上半年均線",
                            style={"color": "red", "fontWeight": "bold"},
                        ),
                        html.Span(f" (現價: {close:.2f}, 120日均價: {ma120:.0f})"),
                    ]
                )
            )
        else:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "❌ 低於半年均線",
                            style={"color": "green", "fontWeight": "bold"},
                        ),
                        html.Span(f" (現價: {close:.2f}, 120日均價: {ma120:.0f})"),
                    ]
                )
            )

    return analyses


def generate_macd_analysis(df, index_name="加權指數"):
    """
    生成 MACD 分析文字

    Args:
        df: DataFrame，包含完整歷史資料
        index_name: 指數名稱
    """
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    analyses = []

    # DIF 分析
    if pd.notna(latest["DIF"]):
        dif = latest["DIF"]
        if dif > 0:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            f"📈 {index_name} DIF 大於 0",
                            style={"color": "red", "fontWeight": "bold"},
                        ),
                        html.Span(f" (DIF: {dif:.2f})"),
                    ]
                )
            )
        else:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            f"📉 {index_name} DIF 小於 0",
                            style={"color": "green", "fontWeight": "bold"},
                        ),
                        html.Span(f" (DIF: {dif:.2f})"),
                    ]
                )
            )

    # MACD 柱狀體分析
    if pd.notna(latest["MACD_Hist"]):
        hist = latest["MACD_Hist"]

        # 當前柱狀體顏色
        if hist > 0:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "🔴 柱狀體紅色",
                            style={"color": "#ef5350", "fontWeight": "bold"},
                        ),
                        html.Span(f" (MACD Hist: {hist:.2f})"),
                    ]
                )
            )
        else:
            analyses.append(
                html.Li(
                    [
                        html.Span(
                            "🟢 柱狀體綠色",
                            style={"color": "#26a69a", "fontWeight": "bold"},
                        ),
                        html.Span(f" (MACD Hist: {hist:.2f})"),
                    ]
                )
            )

        # 與前一日比較
        if prev is not None and pd.notna(prev["MACD_Hist"]):
            prev_hist = prev["MACD_Hist"]

            if prev_hist < 0 and hist > 0:
                analyses.append(
                    html.Li(
                        [
                            html.Span(
                                "🔄 柱狀體綠轉紅",
                                style={
                                    "color": "#ef5350",
                                    "fontWeight": "bold",
                                    "fontSize": "1.1em",
                                },
                            ),
                            html.Span(f" (前: {prev_hist:.2f} → 現: {hist:.2f})"),
                        ]
                    )
                )
            elif prev_hist > 0 and hist < 0:
                analyses.append(
                    html.Li(
                        [
                            html.Span(
                                "🔄 柱狀體紅轉綠",
                                style={
                                    "color": "#26a69a",
                                    "fontWeight": "bold",
                                    "fontSize": "1.1em",
                                },
                            ),
                            html.Span(f" (前: {prev_hist:.2f} → 現: {hist:.2f})"),
                        ]
                    )
                )
            elif hist > 0 and prev_hist > 0:
                if hist > prev_hist:
                    analyses.append(
                        html.Li(
                            [
                                html.Span(
                                    "📊 紅柱增長",
                                    style={"color": "#d32f2f", "fontWeight": "bold"},
                                ),
                                html.Span(
                                    f" (前: {prev_hist:.2f} → 現: {hist:.2f}, +{hist-prev_hist:.2f})"
                                ),
                            ]
                        )
                    )
                else:
                    analyses.append(
                        html.Li(
                            [
                                html.Span(
                                    "📉 紅柱縮小",
                                    style={"color": "#ff6f61", "fontWeight": "bold"},
                                ),
                                html.Span(
                                    f" (前: {prev_hist:.2f} → 現: {hist:.2f}, {hist-prev_hist:.2f})"
                                ),
                            ]
                        )
                    )
            elif hist < 0 and prev_hist < 0:
                if abs(hist) > abs(prev_hist):
                    analyses.append(
                        html.Li(
                            [
                                html.Span(
                                    "📊 綠柱增長",
                                    style={"color": "#1b5e20", "fontWeight": "bold"},
                                ),
                                html.Span(
                                    f" (前: {prev_hist:.2f} → 現: {hist:.2f}, {hist-prev_hist:.2f})"
                                ),
                            ]
                        )
                    )
                else:
                    analyses.append(
                        html.Li(
                            [
                                html.Span(
                                    "📈 綠柱縮小",
                                    style={"color": "#4caf50", "fontWeight": "bold"},
                                ),
                                html.Span(
                                    f" (前: {prev_hist:.2f} → 現: {hist:.2f}, {hist-prev_hist:.2f})"
                                ),
                            ]
                        )
                    )

    return analyses


# 頁面布局
layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "📊 即時盤勢分析",
                            className="text-center mb-4",
                            style={"color": "#2c3e50", "fontWeight": "bold"},
                        ),
                        html.Hr(
                            style={"border-color": "#00a896", "border-width": "2px"}
                        ),
                    ],
                    width=12,
                )
            ]
        ),
        # 自動更新控制
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
                                                html.Label(
                                                    "自動更新間隔（秒）:",
                                                    style={
                                                        "fontWeight": "bold",
                                                        "marginRight": "10px",
                                                    },
                                                ),
                                                dcc.Input(
                                                    id="update-interval-input",
                                                    type="number",
                                                    value=30,  # 改成 30 秒
                                                    min=10,
                                                    max=300,
                                                    step=10,
                                                    style={
                                                        "width": "100px",
                                                        "marginRight": "20px",
                                                    },
                                                ),
                                                dbc.Button(
                                                    "🔄 立即更新",
                                                    id="manual-update-btn",
                                                    color="primary",
                                                    size="sm",
                                                ),
                                                html.Span(
                                                    id="last-update-time",
                                                    style={
                                                        "marginLeft": "20px",
                                                        "color": "#666",
                                                    },
                                                ),
                                            ],
                                            style={
                                                "display": "flex",
                                                "alignItems": "center",
                                            },
                                        )
                                    ]
                                )
                            ],
                            className="mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # 間隔更新組件
        dcc.Interval(
            id="interval-component", interval=30 * 1000, n_intervals=0  # 預設 30 秒
        ),
        # 加權指數和櫃買指數並排顯示
        dbc.Row(
            [
                # 左側: 加權指數
                dbc.Col(
                    [
                        html.H3(
                            "📈 台股加權指數",
                            className="mb-3",
                            style={"color": "#1976d2"},
                        ),
                        dcc.Loading(
                            id="loading-tse",
                            type="default",
                            children=[
                                dcc.Graph(
                                    id="tse-chart",
                                    config={"displayModeBar": True},
                                    style={"height": "600px"},
                                ),
                            ],
                        ),
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H5(
                                        "📊 技術分析",
                                        style={"color": "#1976d2", "margin": 0},
                                    )
                                ),
                                dbc.CardBody(
                                    [
                                        html.H6(
                                            "均線分析",
                                            className="mb-2",
                                            style={"fontWeight": "bold"},
                                        ),
                                        html.Ul(
                                            id="tse-ma-analysis",
                                            style={
                                                "lineHeight": "1.6",
                                                "fontSize": font_size,
                                            },
                                        ),
                                        html.Hr(),
                                        html.H6(
                                            "MACD 分析",
                                            className="mb-2",
                                            style={"fontWeight": "bold"},
                                        ),
                                        html.Ul(
                                            id="tse-macd-analysis",
                                            style={
                                                "lineHeight": "1.6",
                                                "fontSize": font_size,
                                            },
                                        ),
                                    ]
                                ),
                            ],
                            className="mb-4",
                        ),
                    ],
                    width=6,
                ),  # 左側佔一半
                # 右側: 櫃買指數
                dbc.Col(
                    [
                        html.H3(
                            "📈 櫃買指數", className="mb-3", style={"color": "#d32f2f"}
                        ),
                        dcc.Loading(
                            id="loading-otc",
                            type="default",
                            children=[
                                dcc.Graph(
                                    id="otc-chart",
                                    config={"displayModeBar": True},
                                    style={"height": "600px"},
                                ),
                            ],
                        ),
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H5(
                                        "📊 技術分析",
                                        style={"color": "#d32f2f", "margin": 0},
                                    )
                                ),
                                dbc.CardBody(
                                    [
                                        html.H6(
                                            "均線分析",
                                            className="mb-2",
                                            style={"fontWeight": "bold"},
                                        ),
                                        html.Ul(
                                            id="otc-ma-analysis",
                                            style={
                                                "lineHeight": "1.6",
                                                "fontSize": font_size,
                                            },
                                        ),
                                        html.Hr(),
                                        html.H6(
                                            "MACD 分析",
                                            className="mb-2",
                                            style={"fontWeight": "bold"},
                                        ),
                                        html.Ul(
                                            id="otc-macd-analysis",
                                            style={
                                                "lineHeight": "1.6",
                                                "fontSize": font_size,
                                            },
                                        ),
                                    ]
                                ),
                            ],
                            className="mb-4",
                        ),
                    ],
                    width=6,
                ),  # 右側佔一半
            ]
        ),
        # 新增處置股和警示股圖表
        html.Hr(
            style={"margin": "40px 0", "border-color": "#00a896", "border-width": "2px"}
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H3(
                            "🚨 處置股與警示股統計",
                            className="text-center mb-4",
                            style={"color": "#2c3e50", "fontWeight": "bold"},
                        ),
                    ],
                    width=12,
                )
            ]
        ),
        dbc.Row(
            [
                # 左側: 處置股數量
                dbc.Col(
                    [
                        html.H4(
                            f"⛔ 處置股數量 (近{days_to_display}天)",
                            className="mb-3",
                            style={"color": "#e74c3c"},
                        ),
                        dcc.Loading(
                            id="loading-disposal",
                            type="default",
                            children=[
                                dcc.Graph(
                                    id="disposal-chart",
                                    config={"displayModeBar": True},
                                    style={"height": "400px"},
                                ),
                            ],
                        ),
                    ],
                    width=6,
                ),
                # 右側: 警示股數量
                dbc.Col(
                    [
                        html.H4(
                            f"⚠️ 警示股數量 (近{days_to_display}天)",
                            className="mb-3",
                            style={"color": "#f39c12"},
                        ),
                        dcc.Loading(
                            id="loading-noticed",
                            type="default",
                            children=[
                                dcc.Graph(
                                    id="noticed-chart",
                                    config={"displayModeBar": True},
                                    style={"height": "400px"},
                                ),
                            ],
                        ),
                    ],
                    width=6,
                ),
            ],
            className="mb-4",
        ),
        # 說明卡片
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "💡 說明",
                                            className="card-title text-info",
                                        ),
                                        html.Ul(
                                            [
                                                html.Li(
                                                    [
                                                        html.Strong("處置股"),
                                                        ": 股價異常波動或交易量異常增加，證交所實施處置措施的股票",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("警示股"),
                                                        ": 股價達到預警標準，可能面臨全額交割或停牌風險的股票",
                                                    ]
                                                ),
                                                html.Li(
                                                    "處置股和警示股通常伴隨較高的投資風險，建議謹慎操作"
                                                ),
                                            ]
                                        ),
                                    ]
                                )
                            ],
                            className="shadow-sm",
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


# Callback: 更新間隔設定
@callback(
    Output("interval-component", "interval"), Input("update-interval-input", "value")
)
def update_interval(seconds):
    if seconds is None or seconds < 10:
        seconds = 60
    return seconds * 1000


# Callback: 更新圖表和分析
@callback(
    [
        Output("tse-chart", "figure"),
        Output("tse-ma-analysis", "children"),
        Output("tse-macd-analysis", "children"),
        Output("otc-chart", "figure"),
        Output("otc-ma-analysis", "children"),
        Output("otc-macd-analysis", "children"),
        Output("disposal-chart", "figure"),
        Output("noticed-chart", "figure"),
        Output("last-update-time", "children"),
    ],
    [
        Input("interval-component", "n_intervals"),
        Input("manual-update-btn", "n_clicks"),
    ],
)
def update_all_charts(n_intervals, n_clicks):
    """
    更新所有圖表和分析

    自動判斷使用真實資料或示範資料
    """

    # ========== 新增:交易時間判斷 ==========
    now = datetime.now()
    current_time = now.time()

    # 判斷是否在交易時間內 (8:45 ~ 14:00)
    trading_start = datetime.strptime("08:45", "%H:%M").time()
    trading_end = datetime.strptime("14:00", "%H:%M").time()
    is_trading_hours = trading_start <= current_time <= trading_end

    # 判斷是否為手動更新
    ctx = dash.callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        is_manual_update = trigger_id == "manual-update-btn"
    else:
        is_manual_update = False

    # 非交易時間 + 非手動更新 = 跳過更新
    if not is_trading_hours and not is_manual_update:
        print(f"⏰ 非交易時間 ({now.strftime('%H:%M:%S')}),跳過自動更新")
        from dash import no_update

        update_time_msg = f"⏰ 非交易時間,暫停更新 (交易時間: 08:45-14:00) | 最後更新: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            update_time_msg,
        )
    # ========== 交易時間判斷結束 ==========

    try:
        # ========== 嘗試使用真實資料 ==========
        if USE_REAL_DATA and api is not None:
            print("📡 使用 Shioaji 真實資料")
            tse_data, otc_data = get_cached_or_fetch(api)

        # ========== 使用示範資料 ==========
        else:
            print("🎭 使用示範資料")
            dates = pd.date_range(end=pd.Timestamp.now(), periods=120, freq="D")

            # TSE 示範資料
            np.random.seed(42)  # 固定種子讓資料穩定
            base_tse = 20000

            # 產生基礎價格走勢
            price_changes = np.random.randn(120).cumsum() * 30
            tse_data = pd.DataFrame(
                {
                    "Close": base_tse + price_changes,
                },
                index=dates,
            )

            # 產生 OHLC (確保邏輯正確)
            tse_data["Open"] = tse_data["Close"].shift(1).fillna(base_tse)
            tse_data["High"] = (
                tse_data[["Open", "Close"]].max(axis=1) + np.random.rand(120) * 100
            )
            tse_data["Low"] = (
                tse_data[["Open", "Close"]].min(axis=1) - np.random.rand(120) * 100
            )
            tse_data["Volume"] = np.random.rand(120) * 1000 + 2000

            # 重新排列欄位順序
            tse_data = tse_data[["Open", "High", "Low", "Close", "Volume"]]

            # 計算均線
            tse_data["ma5"] = tse_data["Close"].rolling(window=5).mean().round(2)
            tse_data["ma20"] = tse_data["Close"].rolling(window=20).mean().round(2)
            tse_data["ma60"] = tse_data["Close"].rolling(window=60).mean().round(2)
            tse_data["ma120"] = tse_data["Close"].rolling(window=120).mean().round(2)

            # 計算 MACD
            import talib

            tse_data["DIF"], tse_data["MACD"], tse_data["MACD_Hist"] = talib.MACD(
                tse_data["Close"].values, fastperiod=12, slowperiod=26, signalperiod=9
            )

            # OTC 示範資料
            base_otc = 240

            # 產生基礎價格走勢
            price_changes_otc = np.random.randn(120).cumsum() * 1.5
            otc_data = pd.DataFrame(
                {
                    "Close": base_otc + price_changes_otc,
                },
                index=dates,
            )

            # 產生 OHLC (確保邏輯正確)
            otc_data["Open"] = otc_data["Close"].shift(1).fillna(base_otc)
            otc_data["High"] = (
                otc_data[["Open", "Close"]].max(axis=1) + np.random.rand(120) * 3
            )
            otc_data["Low"] = (
                otc_data[["Open", "Close"]].min(axis=1) - np.random.rand(120) * 3
            )
            otc_data["Volume"] = np.random.rand(120) * 200 + 400

            # 重新排列欄位順序
            otc_data = otc_data[["Open", "High", "Low", "Close", "Volume"]]

            # 計算均線
            otc_data["ma5"] = otc_data["Close"].rolling(window=5).mean().round(2)
            otc_data["ma20"] = otc_data["Close"].rolling(window=20).mean().round(2)
            otc_data["ma60"] = otc_data["Close"].rolling(window=60).mean().round(2)
            otc_data["ma120"] = otc_data["Close"].rolling(window=120).mean().round(2)

            # 計算 MACD
            otc_data["DIF"], otc_data["MACD"], otc_data["MACD_Hist"] = talib.MACD(
                otc_data["Close"].values, fastperiod=12, slowperiod=26, signalperiod=9
            )

        # ========== 處置股和警示股資料 ==========
        try:
            from finlab_data import get_disposal_stock_count, get_noticed_stock_count

            disposal_count = get_disposal_stock_count(days=days_to_display)
            noticed_count = get_noticed_stock_count(days=days_to_display)
        except Exception as e:
            print(f"⚠️ 載入處置股/警示股資料失敗: {e}")
            # 使用示範資料
            dates_days_to_display = pd.date_range(
                end=pd.Timestamp.now(), periods=days_to_display, freq="D"
            )
            np.random.seed(100)
            disposal_count = pd.Series(
                np.random.randint(5, 25, size=days_to_display),
                index=dates_days_to_display,
            )
            noticed_count = pd.Series(
                np.random.randint(10, 40, size=days_to_display),
                index=dates_days_to_display,
            )

    except Exception as e:
        print(f"❌ 資料載入錯誤: {e}")
        # 回傳空圖表
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text=f"資料載入失敗: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="red"),
        )
        return (
            empty_fig,
            [],
            [],
            empty_fig,
            [],
            [],
            empty_fig,
            empty_fig,
            f"更新失敗: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        )

    # 建立圖表
    tse_fig = create_index_chart_with_macd(tse_data, "台股加權指數")
    otc_fig = create_index_chart_with_macd(otc_data, "櫃買指數")
    disposal_fig = create_stock_count_chart(
        disposal_count, f"處置股數量 (近{days_to_display}天)", color="#e74c3c"
    )
    noticed_fig = create_stock_count_chart(
        noticed_count, f"警示股數量 (近{days_to_display}天)", color="#f39c12"
    )

    # 生成分析
    tse_ma = generate_ma_analysis(tse_data.iloc[-1], "加權指數")
    tse_macd = generate_macd_analysis(tse_data, "加權指數")

    otc_ma = generate_ma_analysis(otc_data.iloc[-1], "櫃買指數")
    otc_macd = generate_macd_analysis(otc_data, "櫃買指數")

    # 更新時間
    update_time = f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return (
        tse_fig,
        tse_ma,
        tse_macd,
        otc_fig,
        otc_ma,
        otc_macd,
        disposal_fig,
        noticed_fig,
        update_time,
    )
