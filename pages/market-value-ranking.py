import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 將專案根目錄加入 Python path
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "data"))  # 加入 data 資料夾

# 使用你原本的 market_value_growth 模組
from data.market_value_growth import analyze_market_value_growth as original_analyze
from finlab import data

# 註冊頁面
dash.register_page(__name__, path="/market-value-ranking", name="市值排行")


def analyze_market_value_growth_for_dash(top_n=100, days=30):
    """包裝原本的分析函數,增加日期資訊"""
    try:
        # 使用原本的分析函數
        df = original_analyze(top_n=top_n, days=days)

        # 取得市值資料以獲取日期資訊
        market_value = data.get("etl:market_value")
        latest_date = market_value.index[-1]
        past_date = market_value.index[-days - 1]

        print(f"✓ 成功分析 {len(df)} 筆資料")
        print(
            f"  期間: {past_date.strftime('%Y-%m-%d')} ~ {latest_date.strftime('%Y-%m-%d')}"
        )

        return df, latest_date, past_date

    except Exception as e:
        print(f"❌ 分析錯誤: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame(), None, None


def create_growth_ranking_chart(df, days=30):
    """建立市值成長率排行圖"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="暫無資料",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        return fig

    try:
        # 找出市值成長率欄位 (可能是 "市值成長率(%)" )
        growth_col = None
        for col in df.columns:
            if "市值成長率" in col:
                growth_col = col
                break

        if growth_col is None:
            print("❌ 找不到市值成長率欄位")
            return go.Figure()

        print(f"使用欄位: {growth_col}")
        print(f"資料型態: {df[growth_col].dtype}")
        print(f"範例值: {df[growth_col].head().tolist()}")

        # 建立處理用的 DataFrame
        df_sorted = df.copy()

        # 將格式化的字串轉回數值
        # 處理 "+5.23%" -> 5.23 或 "-2.10%" -> -2.10 或 "-" -> NaN
        def parse_percentage(val):
            if pd.isna(val) or val == "-" or val == "":
                return np.nan
            try:
                # 移除 % 和 + 符號,轉成 float
                cleaned = str(val).replace("%", "").replace("+", "").strip()
                return float(cleaned)
            except:
                return np.nan

        df_sorted["市值成長率_數值"] = df_sorted[growth_col].apply(parse_percentage)

        # 移除 NaN 並排序
        df_sorted = df_sorted[df_sorted["市值成長率_數值"].notna()]

        if len(df_sorted) == 0:
            print("❌ 沒有有效的成長率資料")
            return go.Figure()

        # 取前 20 名市值成長率最高的
        top_20 = df_sorted.nlargest(20, "市值成長率_數值")

        # 反轉順序,讓最高的在最上面
        top_20 = top_20.iloc[::-1]

        print(f"✓ 取得 {len(top_20)} 筆有效資料")

        # 建立顏色映射 (成長率正負)
        colors = ["#ef5350" if x > 0 else "#26a69a" for x in top_20["市值成長率_數值"]]

        # 建立顯示標籤
        labels = top_20["股票代號"] + " " + top_20["公司名稱"].fillna("")

        # 判斷文字位置 - 如果數值太大就放在內部
        text_positions = []
        for val in top_20["市值成長率_數值"]:
            if abs(val) > 50:  # 成長率超過 50% 就放內部
                text_positions.append("inside")
            else:
                text_positions.append("outside")

        fig = go.Figure(
            data=[
                go.Bar(
                    x=top_20["市值成長率_數值"],
                    y=labels,
                    orientation="h",
                    marker_color=colors,
                    text=top_20[growth_col],  # 使用原始格式化的字串
                    textposition=text_positions,  # 動態調整文字位置
                    textfont=dict(size=11, color="white"),  # 內部文字用白色
                    hovertemplate="<b>%{y}</b><br>"
                    + f"市值成長率: %{{text}}<br>"
                    + "<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title=f"市值成長率排行 TOP 20 ({days}天)",
            xaxis_title="成長率 (%)",
            yaxis_title="",
            height=600,
            showlegend=False,
            margin=dict(l=200, r=100, t=80, b=50),  # 增加右邊距
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            uniformtext=dict(mode="hide", minsize=8),  # 自動隱藏太小的文字
        )

        fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")

        # 調整 x 軸範圍,給文字留空間
        x_min = top_20["市值成長率_數值"].min()
        x_max = top_20["市值成長率_數值"].max()
        x_range_padding = (x_max - x_min) * 0.15  # 15% 的留白
        fig.update_xaxes(range=[x_min - x_range_padding, x_max + x_range_padding])

        return fig

    except Exception as e:
        print(f"❌ 建立成長率圖表錯誤: {e}")
        import traceback

        traceback.print_exc()

        fig = go.Figure()
        fig.add_annotation(
            text=f"圖表錯誤: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="red"),
        )
        return fig


def create_rank_change_chart(df, days=30):
    """建立排名變化圖"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="暫無資料",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        return fig

    try:
        # 找出排名變化欄位
        rank_change_col = None
        for col in df.columns:
            if "排名變化" in col:
                rank_change_col = col
                break

        if rank_change_col is None:
            print("❌ 找不到排名變化欄位")
            return go.Figure()

        print(f"使用欄位: {rank_change_col}")

        # 建立處理用的 DataFrame
        df_copy = df.copy()

        # 將格式化的字串轉回數值
        # 處理 "+5" -> 5 或 "-3" -> -3 或 "-" -> NaN
        def parse_rank_change(val):
            if pd.isna(val) or val == "-" or val == "":
                return np.nan
            try:
                cleaned = str(val).replace("+", "").strip()
                return float(cleaned)
            except:
                return np.nan

        df_copy["排名變化_數值"] = df_copy[rank_change_col].apply(parse_rank_change)

        # 移除 NaN
        df_filtered = df_copy[df_copy["排名變化_數值"].notna()]

        if len(df_filtered) == 0:
            print("❌ 沒有有效的排名變化資料")
            return go.Figure()

        # 取排名變化最大的前 20 名
        top_20 = df_filtered.nlargest(20, "排名變化_數值")

        # 反轉順序,讓最高的在最上面
        top_20 = top_20.iloc[::-1]

        print(f"✓ 取得 {len(top_20)} 筆有效資料")

        # 建立顏色映射
        colors = ["#66bb6a" if x > 0 else "#ef5350" for x in top_20["排名變化_數值"]]

        # 建立顯示標籤
        labels = top_20["股票代號"] + " " + top_20["公司名稱"].fillna("")

        # 判斷文字位置 - 如果數值太大就放在內部
        text_positions = []
        for val in top_20["排名變化_數值"]:
            if abs(val) > 20:  # 排名變化超過 20 就放內部
                text_positions.append("inside")
            else:
                text_positions.append("outside")

        fig = go.Figure(
            data=[
                go.Bar(
                    x=top_20["排名變化_數值"],
                    y=labels,
                    orientation="h",
                    marker_color=colors,
                    text=top_20[rank_change_col],  # 使用原始格式化的字串
                    textposition=text_positions,  # 動態調整文字位置
                    textfont=dict(size=11, color="white"),  # 內部文字用白色
                    hovertemplate="<b>%{y}</b><br>"
                    + "排名變化: %{text}<br>"
                    + "<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title=f"排名爬升 TOP 20 ({days}天)",
            xaxis_title="排名變化",
            yaxis_title="",
            height=600,
            showlegend=False,
            margin=dict(l=200, r=100, t=80, b=50),  # 增加右邊距
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            uniformtext=dict(mode="hide", minsize=8),  # 自動隱藏太小的文字
        )

        fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")

        # 調整 x 軸範圍,給文字留空間
        x_min = top_20["排名變化_數值"].min()
        x_max = top_20["排名變化_數值"].max()
        x_range_padding = (x_max - x_min) * 0.15  # 15% 的留白
        fig.update_xaxes(range=[x_min - x_range_padding, x_max + x_range_padding])

        return fig

    except Exception as e:
        print(f"❌ 建立排名變化圖表錯誤: {e}")
        import traceback

        traceback.print_exc()

        fig = go.Figure()
        fig.add_annotation(
            text=f"圖表錯誤: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="red"),
        )
        return fig


def create_industry_distribution_chart(df):
    """建立產業分布圓餅圖"""
    if df.empty or "產業類別" not in df.columns:
        return go.Figure()

    # 統計產業分布
    industry_counts = df["產業類別"].value_counts().head(10)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=industry_counts.index,
                values=industry_counts.values,
                hole=0.4,
                textinfo="label+percent",
            )
        ]
    )

    fig.update_layout(
        title="產業分布 TOP 10",
        height=400,
        showlegend=True,
        margin=dict(l=50, r=50, t=80, b=50),
    )

    return fig


def create_market_value_table(df, days=30):
    """建立市值排行表格"""
    if df.empty:
        return html.Div("暫無資料")

    # 原本的模組已經格式化好了,直接使用
    # 只需要調整欄位順序
    display_df = df.copy()

    # 確保有所需的欄位
    required_cols = ["目前排名", "股票代號", "公司名稱", "產業類別"]
    available_cols = [col for col in required_cols if col in display_df.columns]

    # 加入其他欄位
    for col in display_df.columns:
        if col not in available_cols and col not in [
            "股票代號",
            "公司名稱",
            "產業類別",
        ]:
            available_cols.append(col)

    display_df = display_df[available_cols]

    # 建立表格
    table = dbc.Table.from_dataframe(
        display_df.head(50),
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
        className="table-sm",
    )

    return table


# 頁面布局
layout = dbc.Container(
    [
        # 標題區
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("📊 市值排行分析", className="mb-3 text-primary"),
                        html.P(
                            "分析指定期間內市值的成長率與排名變化",
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
                                        html.H5("⚙️ 分析參數", className="card-title"),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "分析前 N 名:",
                                                            className="fw-bold",
                                                        ),
                                                        dcc.Slider(
                                                            id="top-n-slider",
                                                            min=50,
                                                            max=300,
                                                            step=50,
                                                            value=300,
                                                            marks={
                                                                50: "50",
                                                                100: "100",
                                                                150: "150",
                                                                200: "200",
                                                                250: "250",
                                                                300: "300",
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "分析天數:",
                                                            className="fw-bold",
                                                        ),
                                                        dcc.Slider(
                                                            id="days-slider",
                                                            min=1,
                                                            max=90,
                                                            step=5,
                                                            value=30,
                                                            marks={
                                                                5: "5天",
                                                                30: "30天",
                                                                60: "60天",
                                                                90: "90天",
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Button(
                                            "🔄 更新分析",
                                            id="market-value-update-btn",
                                            color="primary",
                                            className="w-100",
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
            id="market-value-loading",
            type="default",
            children=[
                # 摘要卡片
                dbc.Row(id="summary-cards", className="mb-4"),
                # 圖表區域
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                dcc.Graph(
                                                    id="growth-ranking-chart",
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
                                                    id="rank-change-chart",
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
                # 產業分布
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                dcc.Graph(
                                                    id="industry-distribution-chart",
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
                # 詳細表格
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H5(
                                                "📋 市值排行詳細表",
                                                className="mb-0",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [html.Div(id="market-value-table")]
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
                                                        html.Strong("市值成長率"),
                                                        ": 指定期間內市值的成長百分比",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("排名變化"),
                                                        ": 正數表示排名上升(往前爬),負數表示排名下降",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("產業分布"),
                                                        ": 顯示市值前 N 名中各產業的占比",
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
        Output("summary-cards", "children"),
        Output("growth-ranking-chart", "figure"),
        Output("rank-change-chart", "figure"),
        Output("industry-distribution-chart", "figure"),
        Output("market-value-table", "children"),
    ],
    [
        Input("market-value-update-btn", "n_clicks"),
        Input("top-n-slider", "value"),
        Input("days-slider", "value"),
    ],
    prevent_initial_call=False,  # 允許初始載入
)
def update_market_value_analysis(n_clicks, top_n, days):
    """更新市值分析"""
    try:
        print(f"\n{'='*60}")
        print(f"🔄 更新市值分析:")
        print(f"  - top_n: {top_n}")
        print(f"  - days: {days}")
        print(f"  - n_clicks: {n_clicks}")
        print(f"{'='*60}")

        # 分析市值成長
        df, latest_date, past_date = analyze_market_value_growth_for_dash(
            top_n=top_n, days=days
        )

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
            return [], empty_fig, empty_fig, empty_fig, html.Div("暫無資料")

        print(f"✓ 成功取得 {len(df)} 筆資料")
        print(f"  欄位: {df.columns.tolist()}")

        # 計算摘要統計 - 處理格式化的字串
        # 找出市值成長率欄位
        growth_col = None
        for col in df.columns:
            if "市值成長率" in col:
                growth_col = col
                break

        if growth_col:
            # 將 "市值成長率(%)" 欄位轉換回數值
            def parse_percentage(val):
                if pd.isna(val) or val == "-" or val == "":
                    return np.nan
                try:
                    cleaned = str(val).replace("%", "").replace("+", "").strip()
                    return float(cleaned)
                except:
                    return np.nan

            growth_rates = df[growth_col].apply(parse_percentage)
            avg_growth = growth_rates.mean()
            positive_count = (growth_rates > 0).sum()
            total_count = len(df)
        else:
            avg_growth = 0
            positive_count = 0
            total_count = len(df)

        print(f"  平均成長率: {avg_growth:.2f}%")
        print(f"  上漲家數: {positive_count}/{total_count}")

        # 建立摘要卡片
        summary_cards = [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("分析期間", className="text-muted"),
                                    html.H4(
                                        f"{past_date.strftime('%Y-%m-%d')} ~ {latest_date.strftime('%Y-%m-%d')}",
                                        className="mb-0",
                                        style={"fontSize": "1.2rem"},
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=4,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("平均成長率", className="text-muted"),
                                    html.H4(
                                        f"{avg_growth:+.2f}%",
                                        className="mb-0",
                                        style={
                                            "color": (
                                                "#ef5350"
                                                if avg_growth > 0
                                                else "#26a69a"
                                            )
                                        },
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=4,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("上漲家數", className="text-muted"),
                                    html.H4(
                                        f"{positive_count} / {total_count}",
                                        className="mb-0 text-success",
                                    ),
                                ]
                            )
                        ],
                        className="shadow-sm",
                    )
                ],
                width=4,
            ),
        ]

        # 建立圖表
        print("📊 建立圖表中...")
        growth_chart = create_growth_ranking_chart(df, days)
        rank_chart = create_rank_change_chart(df, days)
        industry_chart = create_industry_distribution_chart(df)
        table = create_market_value_table(df, days)

        print("✓ 圖表建立完成")

        return summary_cards, growth_chart, rank_chart, industry_chart, table

    except Exception as e:
        print(f"❌ 更新市值分析錯誤: {e}")
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
        return [], empty_fig, empty_fig, empty_fig, html.Div(f"錯誤: {str(e)}")
