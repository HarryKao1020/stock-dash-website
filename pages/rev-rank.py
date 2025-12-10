import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

# 將專案根目錄加入 Python path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from finlab_data import finlab_data

# 註冊頁面
dash.register_page(__name__, path="/rev-rank", name="月營收排行")


def create_revenue_yoy_chart(df, top_n=30):
    """
    建立營收年增率排行柱狀圖

    Args:
        df: 營收排行 DataFrame
        top_n: 顯示前幾名
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="無資料",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="gray"),
        )
        return fig

    # 取前 N 名並反轉順序(最高在上)
    display_df = df.head(top_n).iloc[::-1].copy()

    # 建立顯示標籤
    display_df["顯示標籤"] = (
        display_df["股票代號"] + " " + display_df["公司名稱"].fillna("")
    )

    # 顏色: 正數紅色，負數綠色
    colors = ["#ef5350" if x >= 0 else "#26a69a" for x in display_df["營收YoY(%)"]]

    # 🆕 文字位置: 負數或超過1000%的顯示在內部，其他顯示在外部
    text_positions = [
        "inside" if (x < 0 or x >= 1000) else "outside"
        for x in display_df["營收YoY(%)"]
    ]

    # 🆕 文字顏色: 內部用白色，外部用深色
    text_colors = [
        "white" if (x < 0 or x >= 1000) else "#333" for x in display_df["營收YoY(%)"]
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=display_df["營收YoY(%)"],
                y=display_df["顯示標籤"],
                orientation="h",
                marker_color=colors,
                text=display_df["營收YoY(%)"].apply(lambda x: f"{x:+.1f}%"),
                textposition=text_positions,
                textfont=dict(size=10, color=text_colors),
                hovertemplate="<b>%{y}</b><br>"
                + "營收年增率: %{x:.2f}%<br>"
                + "<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text=f"📈 營收年增率 (YoY) TOP {top_n}",
            font=dict(size=18, color="#2c3e50"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title="年增率 (%)",
            gridcolor="rgba(128,128,128,0.2)",
        ),
        yaxis=dict(title=""),
        height=max(500, top_n * 22),
        margin=dict(l=180, r=80, t=60, b=50),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )

    return fig


def create_revenue_mom_chart(df, top_n=30):
    """
    建立營收月增率排行柱狀圖

    Args:
        df: 營收排行 DataFrame
        top_n: 顯示前幾名
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="無資料",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="gray"),
        )
        return fig

    # 依 MoM 排序取前 N 名並反轉順序
    display_df = (
        df.sort_values("營收MoM(%)", ascending=False).head(top_n).iloc[::-1].copy()
    )

    # 建立顯示標籤
    display_df["顯示標籤"] = (
        display_df["股票代號"] + " " + display_df["公司名稱"].fillna("")
    )

    # 顏色: 正數紅色，負數綠色
    colors = ["#ef5350" if x >= 0 else "#26a69a" for x in display_df["營收MoM(%)"]]

    # 🆕 文字位置: 負數或超過1000%的顯示在內部，其他顯示在外部
    text_positions = [
        "inside" if (x < 0 or x >= 1000) else "outside"
        for x in display_df["營收MoM(%)"]
    ]

    # 🆕 文字顏色: 內部用白色，外部用深色
    text_colors = [
        "white" if (x < 0 or x >= 1000) else "#333" for x in display_df["營收MoM(%)"]
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=display_df["營收MoM(%)"],
                y=display_df["顯示標籤"],
                orientation="h",
                marker_color=colors,
                text=display_df["營收MoM(%)"].apply(lambda x: f"{x:+.1f}%"),
                textposition=text_positions,
                textfont=dict(size=10, color=text_colors),
                hovertemplate="<b>%{y}</b><br>"
                + "營收月增率: %{x:.2f}%<br>"
                + "<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text=f"📊 營收月增率 (MoM) TOP {top_n}",
            font=dict(size=18, color="#2c3e50"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title="月增率 (%)",
            gridcolor="rgba(128,128,128,0.2)",
        ),
        yaxis=dict(title=""),
        height=max(500, top_n * 22),
        margin=dict(l=180, r=80, t=60, b=50),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )

    return fig


def create_ma_distribution_chart(df):
    """
    建立均線排列分布圓餅圖

    Args:
        df: 營收排行 DataFrame
    """
    if df.empty or "均線排列" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="無資料",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="gray"),
        )
        return fig

    # 統計各種均線排列的數量
    ma_counts = df["均線排列"].value_counts()

    # 定義顏色
    color_map = {
        "多頭排列": "#ef5350",
        "谷底反彈": "#ff9800",
        "短期修正": "#2196f3",
        "空頭排列": "#26a69a",
        "盤整": "#9e9e9e",
        "資料不足": "#bdbdbd",
        "N/A": "#e0e0e0",
    }

    colors = [color_map.get(label, "#9e9e9e") for label in ma_counts.index]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=ma_counts.index,
                values=ma_counts.values,
                hole=0.4,
                marker_colors=colors,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>"
                + "數量: %{value} 支<br>"
                + "占比: %{percent}<br>"
                + "<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text="📊 均線排列分布",
            font=dict(size=18, color="#2c3e50"),
            x=0.5,
            xanchor="center",
        ),
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=50, r=50, t=60, b=80),
    )

    return fig


def get_ma_status_style(status):
    """根據均線排列狀態返回對應的樣式"""
    style_map = {
        "多頭排列": {"backgroundColor": "#ffebee", "color": "#c62828"},
        "谷底反彈": {"backgroundColor": "#fff3e0", "color": "#e65100"},
        "短期修正": {"backgroundColor": "#e3f2fd", "color": "#1565c0"},
        "空頭排列": {"backgroundColor": "#e8f5e9", "color": "#2e7d32"},
        "盤整": {"backgroundColor": "#f5f5f5", "color": "#616161"},
        "資料不足": {"backgroundColor": "#fafafa", "color": "#9e9e9e"},
        "N/A": {"backgroundColor": "#fafafa", "color": "#bdbdbd"},
    }
    return style_map.get(status, {"backgroundColor": "#fafafa", "color": "#757575"})


# 頁面布局
layout = dbc.Container(
    [
        # 標題區
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("📈 月營收排行榜", className="mb-3 text-primary"),
                        html.P(
                            "顯示最新月營收年增率 (YoY) 與月增率 (MoM) 排行，並結合均線排列分析",
                            className="text-muted",
                        ),
                        html.Hr(),
                    ],
                    width=12,
                )
            ]
        ),
        # 控制面板
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5("⚙️ 查詢參數", className="card-title"),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "排序依據:",
                                                            className="fw-bold",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="rev-sort-by",
                                                            options=[
                                                                {
                                                                    "label": "營收年增率 (YoY)",
                                                                    "value": "yoy",
                                                                },
                                                                {
                                                                    "label": "營收月增率 (MoM)",
                                                                    "value": "mom",
                                                                },
                                                                {
                                                                    "label": "本月營收",
                                                                    "value": "revenue",
                                                                },
                                                                {
                                                                    "label": "成交金額",
                                                                    "value": "amount",
                                                                },
                                                            ],
                                                            value="yoy",
                                                            clearable=False,
                                                        ),
                                                    ],
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "圖表顯示筆數:",
                                                            className="fw-bold",
                                                        ),
                                                        dcc.Slider(
                                                            id="rev-chart-n-slider",
                                                            min=10,
                                                            max=50,
                                                            step=5,
                                                            value=30,
                                                            marks={
                                                                10: "10",
                                                                20: "20",
                                                                30: "30",
                                                                40: "40",
                                                                50: "50",
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "下方表格顯示筆數:",
                                                            className="fw-bold",
                                                        ),
                                                        dcc.Slider(
                                                            id="rev-top-n-slider",
                                                            min=20,
                                                            max=200,
                                                            step=10,
                                                            value=50,
                                                            marks={
                                                                20: "20",
                                                                50: "50",
                                                                80: "80",
                                                                100: "100",
                                                                150: "150",
                                                                200: "200",
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "🔄 更新資料",
                                                            id="rev-update-btn",
                                                            color="primary",
                                                            className="w-100",
                                                        ),
                                                    ],
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Div(
                                                            id="rev-data-date",
                                                            className="text-muted pt-2",
                                                        )
                                                    ],
                                                    width=9,
                                                ),
                                            ]
                                        ),
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
        # 載入提示
        dcc.Loading(
            id="loading-rev-rank",
            type="default",
            children=[
                # 摘要卡片
                dbc.Row(id="rev-summary-cards", className="mb-4"),
                # 圖表區 - 第一排: YoY 和 MoM 並排
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                dcc.Graph(
                                                    id="rev-yoy-chart",
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
                                                    id="rev-mom-chart",
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
                # 圖表區 - 第二排: 均線分布
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                dcc.Graph(
                                                    id="rev-ma-distribution-chart",
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
                                        dbc.CardHeader(
                                            html.H5("📋 均線排列說明", className="mb-0")
                                        ),
                                        dbc.CardBody(
                                            [
                                                html.Div(
                                                    [
                                                        html.Div(
                                                            [
                                                                html.Span(
                                                                    "🔴 多頭排列",
                                                                    style={
                                                                        "fontWeight": "bold",
                                                                        "color": "#c62828",
                                                                    },
                                                                ),
                                                                html.Span(
                                                                    ": 5MA > 20MA > 60MA，趨勢向上"
                                                                ),
                                                            ],
                                                            className="mb-2",
                                                        ),
                                                        html.Div(
                                                            [
                                                                html.Span(
                                                                    "🟠 谷底反彈",
                                                                    style={
                                                                        "fontWeight": "bold",
                                                                        "color": "#e65100",
                                                                    },
                                                                ),
                                                                html.Span(
                                                                    ": 5MA > 20MA，20MA < 60MA，短線反彈"
                                                                ),
                                                            ],
                                                            className="mb-2",
                                                        ),
                                                        html.Div(
                                                            [
                                                                html.Span(
                                                                    "🔵 短期修正",
                                                                    style={
                                                                        "fontWeight": "bold",
                                                                        "color": "#1565c0",
                                                                    },
                                                                ),
                                                                html.Span(
                                                                    ": 5MA < 20MA，20MA > 60MA，短線回檔"
                                                                ),
                                                            ],
                                                            className="mb-2",
                                                        ),
                                                        html.Div(
                                                            [
                                                                html.Span(
                                                                    "🟢 空頭排列",
                                                                    style={
                                                                        "fontWeight": "bold",
                                                                        "color": "#2e7d32",
                                                                    },
                                                                ),
                                                                html.Span(
                                                                    ": 5MA < 20MA < 60MA，趨勢向下"
                                                                ),
                                                            ],
                                                            className="mb-2",
                                                        ),
                                                    ]
                                                )
                                            ]
                                        ),
                                    ],
                                    className="shadow-sm mb-4 h-100",
                                )
                            ],
                            width=6,
                        ),
                    ]
                ),
                # 詳細表格
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H5(
                                                "📋 月營收排行詳細表", className="mb-0"
                                            )
                                        ),
                                        dbc.CardBody(
                                            [html.Div(id="rev-ranking-table")]
                                        ),
                                    ],
                                    className="shadow-sm",
                                )
                            ],
                            width=12,
                        )
                    ]
                ),
            ],
        ),
        # 說明區
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "💡 指標說明",
                                            className="card-title text-info",
                                        ),
                                        html.Ul(
                                            [
                                                html.Li(
                                                    [
                                                        html.Strong("營收年增率 (YoY)"),
                                                        ": 與去年同月比較的成長率，反映長期成長趨勢",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("營收月增率 (MoM)"),
                                                        ": 與上個月比較的成長率，反映短期營運動能",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("均線排列"),
                                                        ": 根據 5日、20日、60日 均線相對位置判斷趨勢方向",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("選股參考"),
                                                        ": YoY 高 + 均線多頭排列 = 營收成長且股價趨勢向上，值得關注",
                                                    ]
                                                ),
                                            ]
                                        ),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=12,
                )
            ],
            className="mt-4",
        ),
    ],
    fluid=True,
    className="p-4",
)


@callback(
    [
        Output("rev-summary-cards", "children"),
        Output("rev-yoy-chart", "figure"),
        Output("rev-mom-chart", "figure"),
        Output("rev-ma-distribution-chart", "figure"),
        Output("rev-ranking-table", "children"),
        Output("rev-data-date", "children"),
    ],
    [
        Input("rev-update-btn", "n_clicks"),
        Input("rev-sort-by", "value"),
        Input("rev-top-n-slider", "value"),
        Input("rev-chart-n-slider", "value"),
    ],
    prevent_initial_call=False,
)
def update_revenue_ranking(n_clicks, sort_by, top_n, chart_n):
    """更新月營收排行"""
    try:
        print(f"\n{'='*60}")
        print(f"🔄 更新月營收排行:")
        print(f"  - sort_by: {sort_by}")
        print(f"  - top_n: {top_n}")
        print(f"  - chart_n: {chart_n}")
        print(f"{'='*60}")

        # 取得營收排行資料
        df, rev_date = finlab_data.get_revenue_ranking(sort_by=sort_by, top_n=top_n)

        if df.empty:
            print("❌ DataFrame 是空的")
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="無法取得資料",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color="red"),
            )
            return (
                [],
                empty_fig,
                empty_fig,
                empty_fig,
                html.Div("暫無資料"),
                "無法取得資料日期",
            )

        print(f"✓ 成功取得 {len(df)} 筆資料")

        # 計算統計資訊
        avg_yoy = df["營收YoY(%)"].mean()
        avg_mom = df["營收MoM(%)"].mean()
        positive_yoy_count = (df["營收YoY(%)"] > 0).sum()
        positive_mom_count = (df["營收MoM(%)"] > 0).sum()
        bullish_count = (df["均線排列"] == "多頭排列").sum()

        # 建立摘要卡片
        summary_cards = [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("營收資料月份", className="text-muted"),
                                    html.H4(
                                        f"{rev_date.strftime('%Y年%m月')}",
                                        className="mb-0 text-primary",
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("平均年增率", className="text-muted"),
                                    html.H4(
                                        f"{avg_yoy:+.1f}%",
                                        className="mb-0",
                                        style={
                                            "color": (
                                                "#ef5350" if avg_yoy > 0 else "#26a69a"
                                            )
                                        },
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("平均月增率", className="text-muted"),
                                    html.H4(
                                        f"{avg_mom:+.1f}%",
                                        className="mb-0",
                                        style={
                                            "color": (
                                                "#ef5350" if avg_mom > 0 else "#26a69a"
                                            )
                                        },
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("YoY 正成長", className="text-muted"),
                                    html.H4(
                                        f"{positive_yoy_count} / {len(df)}",
                                        className="mb-0 text-success",
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("MoM 正成長", className="text-muted"),
                                    html.H4(
                                        f"{positive_mom_count} / {len(df)}",
                                        className="mb-0 text-info",
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("多頭排列", className="text-muted"),
                                    html.H4(
                                        f"{bullish_count} 支",
                                        className="mb-0 text-danger",
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=2,
            ),
        ]

        # 建立圖表
        yoy_chart = create_revenue_yoy_chart(df, chart_n)
        mom_chart = create_revenue_mom_chart(df, chart_n)
        ma_chart = create_ma_distribution_chart(df)

        # 建立表格
        display_df = df[
            [
                "排名",
                "股票代號",
                "公司名稱",
                "本月營收(億)",
                "營收YoY(%)",
                "營收MoM(%)",
                "成交金額(億)",
                "均線排列",
            ]
        ].copy()

        # 格式化數值
        display_df["本月營收(億)"] = display_df["本月營收(億)"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "-"
        )
        display_df["營收YoY(%)"] = display_df["營收YoY(%)"].apply(
            lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
        )
        display_df["營收MoM(%)"] = display_df["營收MoM(%)"].apply(
            lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
        )
        display_df["成交金額(億)"] = display_df["成交金額(億)"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "-"
        )

        table = dbc.Table.from_dataframe(
            display_df,
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table-sm",
        )

        # 資料日期顯示
        date_str = (
            f"📅 營收資料月份: {rev_date.strftime('%Y年%m月')} | 成交金額: 最新交易日"
        )

        print("✓ 更新完成")

        return (
            summary_cards,
            yoy_chart,
            mom_chart,
            ma_chart,
            table,
            date_str,
        )

    except Exception as e:
        print(f"❌ 更新營收排行錯誤: {e}")
        import traceback

        traceback.print_exc()

        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text=f"發生錯誤: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="red"),
        )
        return (
            [],
            empty_fig,
            empty_fig,
            empty_fig,
            html.Div(f"錯誤: {str(e)}"),
            "錯誤",
        )
