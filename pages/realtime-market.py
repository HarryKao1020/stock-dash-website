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
    from data.shioaji_data import get_cached_or_fetch

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
    print(f"登入失敗")


dash.register_page(__name__, path="/realtime-market", name="即時盤勢")

font_size = "1rem"
days_to_display = 60  # 處置股/警示股顯示天數


def create_index_chart_with_macd(df, title="加權指數"):
    """
    建立包含 K線、均線、成交金額和 MACD 的圖表

    Args:
        df: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Amount', 'ma5', 'ma20', 'ma60', 'ma120', 'DIF', 'MACD', 'MACD_Hist']
        title: 圖表標題
    """
    # 🆕 確保資料不含週末，並轉換索引格式
    df = df.copy()
    df = df[df.index.dayofweek < 5]  # 移除週六日
    df = df.dropna(subset=["Open", "High", "Low", "Close"])  # 移除空資料

    # 🆕 將索引轉換為字串格式，用於 category 類型 x 軸
    df.index = df.index.strftime("%Y-%m-%d")

    # 建立子圖 (K線+均線, 成交金額, MACD)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.5, 0.2, 0.3],
        subplot_titles=(f"{title} K線圖", "成交金額", "MACD"),
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

    # === 第二張圖: 成交金額 ===
    colors = [
        "#ef5350" if close >= open_ else "#26a69a"
        for close, open_ in zip(df["Close"], df["Open"])
    ]

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Amount"],
            name="成交金額",
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

    # 🆕 使用 category 類型 x 軸來移除假日空白
    fig.update_xaxes(type="category", row=1, col=1)
    fig.update_xaxes(type="category", row=2, col=1)
    fig.update_xaxes(type="category", title_text="日期", row=3, col=1)

    # 更新軸標籤
    fig.update_yaxes(title_text="價格", row=1, col=1)
    fig.update_yaxes(title_text="成交金額(億)", row=2, col=1)
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
            y=0.95,
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

    # ===== 均線排列結論 =====
    ma5 = latest_data.get("ma5")
    ma20 = latest_data.get("ma20")
    ma60 = latest_data.get("ma60")

    if pd.notna(ma5) and pd.notna(ma20) and pd.notna(ma60):
        # 判斷均線排列
        if ma5 > ma20 and ma20 > ma60:
            # 多頭排列
            conclusion_text = "📊 多頭排列"
            conclusion_color = "#d32f2f"  # 深紅色
            conclusion_desc = "5MA > 20MA > 60MA，趨勢向上"
        elif ma5 < ma20 and ma20 > ma60 and ma5 > ma60:
            # 多頭短期修正
            conclusion_text = "📊 多頭短期修正"
            conclusion_color = "#ff9800"  # 橘色
            conclusion_desc = "5MA < 20MA，但 5MA > 60MA，短線回檔"
        elif ma5 > ma20 and ma20 < ma60 and ma5 < ma60:
            # 空頭短期反彈
            conclusion_text = "📊 空頭短期反彈"
            conclusion_color = "#2196f3"  # 藍色
            conclusion_desc = "5MA > 20MA，但 5MA < 60MA，短線反彈"
        elif ma5 < ma20 and ma20 < ma60:
            # 空頭排列
            conclusion_text = "📊 空頭排列"
            conclusion_color = "#1b5e20"  # 深綠色
            conclusion_desc = "5MA < 20MA < 60MA，趨勢向下"
        else:
            # 其他情況（盤整）
            conclusion_text = "📊 均線糾結"
            conclusion_color = "#666666"  # 灰色
            conclusion_desc = "均線交錯，趨勢不明"

        analyses.append(
            html.Li(
                [
                    html.Span("─" * 20, style={"color": "#ccc"}),
                ],
                style={"listStyleType": "none", "marginTop": "10px"},
            )
        )
        analyses.append(
            html.Li(
                [
                    html.Span(
                        f"結論: {conclusion_text}",
                        style={
                            "color": conclusion_color,
                            "fontWeight": "bold",
                            "fontSize": "1.1em",
                        },
                    ),
                ],
                style={"listStyleType": "none"},
            )
        )
        analyses.append(
            html.Li(
                [
                    html.Span(
                        conclusion_desc,
                        style={"color": "#666", "fontSize": "0.9em"},
                    ),
                ],
                style={"listStyleType": "none", "marginLeft": "20px"},
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
    # 確保使用原始資料的副本
    df = df.copy()

    # 直接用 iloc 取得最後兩筆資料
    if len(df) < 2:
        return []

    latest_hist = df["MACD_Hist"].iloc[-1]
    prev_hist = df["MACD_Hist"].iloc[-2]
    latest_dif = df["DIF"].iloc[-1]

    analyses = []

    # DIF 分析
    if pd.notna(latest_dif):
        dif = float(latest_dif)
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
    if pd.notna(latest_hist):
        hist = float(latest_hist)

        # 檢查前一天是否有值
        prev_hist_val = float(prev_hist) if pd.notna(prev_hist) else None

        # 當前柱狀體顏色 + 增長/縮短狀態
        if hist > 0:
            # 紅柱
            if prev_hist_val is not None and prev_hist_val > 0:
                # 前一天也是紅柱，比較增長/縮短
                if hist > prev_hist_val:
                    growth_text = "↑ 增長"
                    growth_color = "#d32f2f"
                else:
                    growth_text = "↓ 縮短"
                    growth_color = "#ff6f61"
                analyses.append(
                    html.Li(
                        [
                            html.Span(
                                "🔴 柱狀體紅色",
                                style={"color": "#ef5350", "fontWeight": "bold"},
                            ),
                            html.Span(
                                f" {growth_text}",
                                style={"color": growth_color, "fontWeight": "bold"},
                            ),
                            html.Span(
                                f" (MACD Hist: {hist:.2f}, 前: {prev_hist_val:.2f})"
                            ),
                        ]
                    )
                )
            elif prev_hist_val is not None and prev_hist_val <= 0:
                # 綠轉紅
                analyses.append(
                    html.Li(
                        [
                            html.Span(
                                "🔴 柱狀體紅色",
                                style={"color": "#ef5350", "fontWeight": "bold"},
                            ),
                            html.Span(
                                " 🔄 綠轉紅",
                                style={
                                    "color": "#ef5350",
                                    "fontWeight": "bold",
                                    "fontSize": "1.1em",
                                },
                            ),
                            html.Span(
                                f" (MACD Hist: {hist:.2f}, 前: {prev_hist_val:.2f})"
                            ),
                        ]
                    )
                )
            else:
                # 沒有前一天資料
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
            # 綠柱
            if prev_hist_val is not None and prev_hist_val < 0:
                # 前一天也是綠柱，比較增長/縮短
                # 綠柱增長 = hist 更負 (prev_hist_val > hist)
                if prev_hist_val > hist:
                    growth_text = "↓ 增長"
                    growth_color = "#1b5e20"
                else:
                    growth_text = "↑ 縮短"
                    growth_color = "#4caf50"
                analyses.append(
                    html.Li(
                        [
                            html.Span(
                                "🟢 柱狀體綠色",
                                style={"color": "#26a69a", "fontWeight": "bold"},
                            ),
                            html.Span(
                                f" {growth_text}",
                                style={"color": growth_color, "fontWeight": "bold"},
                            ),
                            html.Span(
                                f" (MACD Hist: {hist:.2f}, 前: {prev_hist_val:.2f})"
                            ),
                        ]
                    )
                )
            elif prev_hist_val is not None and prev_hist_val >= 0:
                # 紅轉綠
                analyses.append(
                    html.Li(
                        [
                            html.Span(
                                "🟢 柱狀體綠色",
                                style={"color": "#26a69a", "fontWeight": "bold"},
                            ),
                            html.Span(
                                " 🔄 紅轉綠",
                                style={
                                    "color": "#26a69a",
                                    "fontWeight": "bold",
                                    "fontSize": "1.1em",
                                },
                            ),
                            html.Span(
                                f" (MACD Hist: {hist:.2f}, 前: {prev_hist_val:.2f})"
                            ),
                        ]
                    )
                )
            else:
                # 沒有前一天資料
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
                                                        html.Div(
                                                            "處置股大部分都是飆股佔比居多,可以視為『 行情很好 』,代表投資人賺錢比例高且追價意願高"
                                                        ),
                                                        html.Div(
                                                            "反之處置股數量減少，可能代表『 行情不好 』，沒有出現上漲的連續性,就沒有飆股,建議減少交易次數"
                                                        ),
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("警示股"),
                                                        html.Div(
                                                            "警示股大部分都是近期漲幅或周轉率高的佔比居多,可以視為『 行情還不錯 』,股價延續性較佳"
                                                        ),
                                                        html.Div(
                                                            "反之警示股數量減少,可能代表『 行情不好 』,股價無延續性,容易買進就套牢,建議減少交易次數"
                                                        ),
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
    Output("interval-component", "interval"),
    Input("update-interval-input", "value"),
    prevent_initial_call=False,
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
    prevent_initial_call=False,
)
def update_all_charts(n_intervals, n_clicks):
    """
    更新所有圖表和分析

    自動判斷使用真實資料或示範資料
    """

    try:
        # ========== 嘗試使用真實資料 ==========
        if USE_REAL_DATA and api is not None:
            print("📡 使用 Shioaji 真實資料")
            tse_data, otc_data = get_cached_or_fetch(api)

        # ========== 使用示範資料 ==========
        else:
            print("🎭 使用示範資料")
            # 生成交易日（不含週末）
            all_dates = pd.date_range(end=pd.Timestamp.now(), periods=180, freq="D")
            dates = all_dates[all_dates.dayofweek < 5][-120:]  # 只保留最近120個交易日

            # TSE 示範資料
            np.random.seed(42)  # 固定種子讓資料穩定
            base_tse = 20000

            # 產生基礎價格走勢
            price_changes = np.random.randn(len(dates)).cumsum() * 30
            tse_data = pd.DataFrame(
                {
                    "Close": base_tse + price_changes,
                },
                index=dates,
            )

            # 產生 OHLC (確保邏輯正確)
            tse_data["Open"] = tse_data["Close"].shift(1).fillna(base_tse)
            tse_data["High"] = (
                tse_data[["Open", "Close"]].max(axis=1)
                + np.random.rand(len(dates)) * 100
            )
            tse_data["Low"] = (
                tse_data[["Open", "Close"]].min(axis=1)
                - np.random.rand(len(dates)) * 100
            )
            tse_data["Amount"] = np.random.rand(len(dates)) * 3000 + 2000  # 成交金額

            # 重新排列欄位順序
            tse_data = tse_data[["Open", "High", "Low", "Close", "Amount"]]

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
            price_changes_otc = np.random.randn(len(dates)).cumsum() * 1.5
            otc_data = pd.DataFrame(
                {
                    "Close": base_otc + price_changes_otc,
                },
                index=dates,
            )

            # 產生 OHLC (確保邏輯正確)
            otc_data["Open"] = otc_data["Close"].shift(1).fillna(base_otc)
            otc_data["High"] = (
                otc_data[["Open", "Close"]].max(axis=1) + np.random.rand(len(dates)) * 3
            )
            otc_data["Low"] = (
                otc_data[["Open", "Close"]].min(axis=1) - np.random.rand(len(dates)) * 3
            )
            otc_data["Amount"] = np.random.rand(len(dates)) * 300 + 400  # 成交金額

            # 重新排列欄位順序
            otc_data = otc_data[["Open", "High", "Low", "Close", "Amount"]]

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
            dates_demo = pd.date_range(
                end=pd.Timestamp.now(), periods=days_to_display, freq="D"
            )
            # 過濾週末
            dates_demo = dates_demo[dates_demo.dayofweek < 5]
            np.random.seed(100)
            disposal_count = pd.Series(
                np.random.randint(5, 25, size=len(dates_demo)),
                index=dates_demo,
            )
            noticed_count = pd.Series(
                np.random.randint(10, 40, size=len(dates_demo)),
                index=dates_demo,
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
