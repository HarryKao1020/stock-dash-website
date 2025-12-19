import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 將專案根目錄加入 Python path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from finlab_data import finlab_data

# 註冊頁面
dash.register_page(__name__, path="/money-flow", name="金流排行")


def get_trading_days_before(target_date, n_days, available_dates):
    """
    取得目標日期往前 n 個交易日

    Args:
        target_date: 目標日期
        n_days: 往前幾個交易日
        available_dates: 可用的交易日列表

    Returns:
        list: 交易日列表
    """
    target_ts = pd.Timestamp(target_date)
    earlier_dates = available_dates[available_dates <= target_ts]

    if len(earlier_dates) < n_days:
        return earlier_dates.tolist()

    return earlier_dates[-n_days:].tolist()


def create_money_flow_chart(target_date, top_n=100):
    """
    建立金流排行柱狀圖

    Args:
        target_date: 目標日期
        top_n: 顯示前幾名
    """
    try:
        # 從 finlab_data 取得資料
        df = finlab_data.amount

        # 找到最接近的交易日
        available_dates = df.index
        target_ts = pd.Timestamp(target_date)

        if target_ts in available_dates:
            actual_date = target_ts
        else:
            # 找最接近且不超過目標日期的交易日
            earlier_dates = available_dates[available_dates <= target_ts]
            if len(earlier_dates) == 0:
                actual_date = available_dates[0]
            else:
                actual_date = earlier_dates[-1]

        day_data = df.loc[actual_date].dropna().astype(float)
        top_stocks = day_data.nlargest(top_n)

        # 建立結果 DataFrame
        result = pd.DataFrame(
            {
                "股票代號": top_stocks.index,
                "成交金額": top_stocks.values,
                "成交金額(億)": top_stocks.values / 1e8,
            }
        )

        # 加入股票名稱
        result["股票名稱"] = result["股票代號"].apply(finlab_data.get_stock_name)
        result["顯示標籤"] = result.apply(
            lambda row: (
                f"{row['股票代號']} {row['股票名稱']}"
                if row["股票名稱"]
                else row["股票代號"]
            ),
            axis=1,
        )

        if result.empty:
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
            return fig, actual_date, result

        # 建立顏色漸層 (金額越高越深)
        max_amount = result["成交金額(億)"].max()
        min_amount = result["成交金額(億)"].min()

        colors = [
            f"rgba(239, 83, 80, {0.4 + 0.6 * (amt - min_amount) / (max_amount - min_amount + 1)})"
            for amt in result["成交金額(億)"]
        ]

        # 建立柱狀圖
        fig = go.Figure(
            data=[
                go.Bar(
                    x=result["顯示標籤"],
                    y=result["成交金額(億)"],
                    marker_color=colors,
                    text=result["成交金額(億)"].apply(lambda x: f"{x:.1f}億"),
                    textposition="outside",
                    textfont=dict(size=10),
                    hovertemplate="<b>%{x}</b><br>"
                    + "成交金額: %{y:.2f} 億<br>"
                    + "<extra></extra>",
                )
            ]
        )

        # 更新布局
        fig.update_layout(
            title=dict(
                text=f"📊 成交金額排行 TOP {top_n} ({actual_date.strftime('%Y-%m-%d')})",
                font=dict(size=20, color="#2c3e50"),
                x=0.5,
                xanchor="center",
            ),
            xaxis=dict(
                title="股票",
                tickangle=45,
                tickfont=dict(size=9),
                categoryorder="total descending",
            ),
            yaxis=dict(
                title="成交金額 (億)",
                gridcolor="rgba(128,128,128,0.2)",
            ),
            height=600,
            margin=dict(l=60, r=30, t=80, b=150),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            hovermode="x unified",
        )

        return fig, actual_date, result

    except Exception as e:
        print(f"❌ 建立金流圖表錯誤: {e}")
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
        return fig, None, pd.DataFrame()


def create_consecutive_ranking_table(target_date, lookback_days=5, top_n=100):
    """
    建立連續進榜統計表

    Args:
        target_date: 目標日期
        lookback_days: 往前看幾天
        top_n: 前幾名算進榜

    Returns:
        DataFrame: 統計結果
    """
    try:
        df = finlab_data.amount
        available_dates = df.index
        target_ts = pd.Timestamp(target_date)

        # 找到實際的交易日
        if target_ts in available_dates:
            actual_date = target_ts
        else:
            earlier_dates = available_dates[available_dates <= target_ts]
            if len(earlier_dates) == 0:
                return pd.DataFrame(), []
            actual_date = earlier_dates[-1]

        # 取得往前 lookback_days 個交易日
        trading_days = get_trading_days_before(
            actual_date, lookback_days, available_dates
        )

        if len(trading_days) == 0:
            return pd.DataFrame(), []

        # 統計每支股票在這些天數中進入前 100 名的次數
        stock_count = {}
        stock_latest_amount = {}  # 記錄最新一天的成交金額

        for i, day in enumerate(trading_days):
            day_data = df.loc[day].dropna().astype(float)
            top_stocks = day_data.nlargest(top_n)

            for stock_id in top_stocks.index:
                if stock_id not in stock_count:
                    stock_count[stock_id] = 0
                stock_count[stock_id] += 1

                # 記錄最後一天的成交金額
                if day == trading_days[-1]:
                    stock_latest_amount[stock_id] = top_stocks[stock_id]

        # 建立結果 DataFrame
        result_data = []
        for stock_id, count in stock_count.items():
            result_data.append(
                {
                    "股票代號": stock_id,
                    "進榜成值前20名累積天數": count,
                    "最新成交金額": stock_latest_amount.get(stock_id, 0),
                    "最新成交金額(億)": stock_latest_amount.get(stock_id, 0) / 1e8,
                }
            )

        result = pd.DataFrame(result_data)

        if result.empty:
            return result, trading_days

        # 加入股票名稱
        result["股票名稱"] = result["股票代號"].apply(finlab_data.get_stock_name)

        # 排序：先按進榜成值前20名累積天數降序，再按成交金額降序
        result = result.sort_values(
            by=["進榜成值前20名累積天數", "最新成交金額"], ascending=[False, False]
        ).reset_index(drop=True)

        # 加入排名
        result.insert(0, "排名", range(1, len(result) + 1))

        return result, trading_days

    except Exception as e:
        print(f"❌ 建立連續進榜統計錯誤: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame(), []


# 取得可用日期範圍
def get_date_range():
    """取得成交金額資料的日期範圍"""
    try:
        df = finlab_data.amount
        return df.index.min(), df.index.max()
    except:
        today = datetime.now()
        return today - timedelta(days=365), today


min_date, max_date = get_date_range()

# 頁面布局
layout = dbc.Container(
    [
        # 標題區
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("💰 金流排行榜", className="mb-3 text-primary"),
                        html.P(
                            "顯示每日成交金額前 100 名的股票/ETF",
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
                                                            "選擇日期:",
                                                            className="fw-bold",
                                                        ),
                                                        html.Div(
                                                            [
                                                                dbc.Button(
                                                                    "◀",
                                                                    id="btn-prev-day",
                                                                    color="secondary",
                                                                    size="sm",
                                                                    className="me-2",
                                                                ),
                                                                dcc.DatePickerSingle(
                                                                    id="date-picker",
                                                                    date=max_date.strftime(
                                                                        "%Y-%m-%d"
                                                                    ),
                                                                    min_date_allowed=min_date.strftime(
                                                                        "%Y-%m-%d"
                                                                    ),
                                                                    max_date_allowed=max_date.strftime(
                                                                        "%Y-%m-%d"
                                                                    ),
                                                                    display_format="YYYY-MM-DD",
                                                                    style={
                                                                        "marginRight": "10px"
                                                                    },
                                                                ),
                                                                dbc.Button(
                                                                    "▶",
                                                                    id="btn-next-day",
                                                                    color="secondary",
                                                                    size="sm",
                                                                ),
                                                            ],
                                                            style={
                                                                "display": "flex",
                                                                "alignItems": "center",
                                                                "marginTop": "8px",
                                                            },
                                                        ),
                                                    ],
                                                    xs=12, sm=12, md=6, lg=6,  # 🔧 RWD: 手機版全寬，桌面版半寬
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "實際交易日:",
                                                            className="fw-bold",
                                                        ),
                                                        html.H4(
                                                            id="actual-date-display",
                                                            className="text-primary mb-0 mt-2",
                                                        ),
                                                    ],
                                                    xs=12, sm=12, md=6, lg=6,  # 🔧 RWD: 手機版全寬，桌面版半寬
                                                ),
                                            ],
                                            className="mb-3",
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
            id="loading-money-flow",
            type="default",
            children=[
                # 摘要卡片
                dbc.Row(id="money-flow-summary-cards", className="mb-4"),
                # 金流圖表
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                dcc.Graph(
                                                    id="money-flow-chart",
                                                    config={
                                                        "displayModeBar": True,
                                                        "displaylogo": False,
                                                    },
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
            ],
        ),
        # 連續進榜統計區
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            "📋 連續進榜統計",
                                            className="mb-0 d-inline",
                                        ),
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        # 天數選擇 Slider (RWD: 手機版一行一個)
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "統計天數:",
                                                            className="fw-bold",
                                                        ),
                                                        dcc.Slider(
                                                            id="lookback-days-slider",
                                                            min=5,
                                                            max=60,
                                                            step=5,
                                                            value=5,
                                                            marks={
                                                                5: "5天",
                                                                10: "10天",
                                                                20: "20天",
                                                                30: "30天",
                                                                40: "40天",
                                                                50: "50天",
                                                                60: "60天",
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
                                                    ],
                                                    xs=12, sm=12, md=6, lg=6,  # 🔧 RWD: 手機版全寬，桌面版半寬
                                                    className="mb-3",
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "統計期間:",
                                                            className="fw-bold",
                                                        ),
                                                        html.P(
                                                            id="lookback-period-display",
                                                            className="text-muted mb-0 mt-2",
                                                        ),
                                                    ],
                                                    xs=12, sm=12, md=6, lg=6,  # 🔧 RWD: 手機版全寬，桌面版半寬
                                                    className="mb-3",
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        # 統計表格
                                        dcc.Loading(
                                            id="loading-ranking-table",
                                            type="default",
                                            children=[
                                                html.Div(id="consecutive-ranking-table")
                                            ],
                                        ),
                                    ]
                                ),
                            ],
                            className="shadow-sm mb-4",
                        )
                    ],
                    width=12,
                )
            ]
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
                                                        html.Strong("成交金額"),
                                                        ": 當日該股票的總交易金額",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("金流集中"),
                                                        ": 金額越高表示市場資金越集中於該股票",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong(
                                                            "進榜成值前20名天數"
                                                        ),
                                                        ": 在統計期間內，進入成交金額前20名的天數",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("連續進榜"),
                                                        ": 天數越多表示該股票持續受到市場資金關注",
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


# Callback: 前一天按鈕
@callback(
    Output("date-picker", "date", allow_duplicate=True),
    Input("btn-prev-day", "n_clicks"),
    State("date-picker", "date"),
    prevent_initial_call=True,
)
def go_prev_day(n_clicks, current_date):
    if n_clicks is None or current_date is None:
        return dash.no_update

    current = datetime.strptime(current_date, "%Y-%m-%d")
    new_date = current - timedelta(days=1)

    # 確保不超過最小日期
    if new_date < min_date:
        new_date = min_date

    return new_date.strftime("%Y-%m-%d")


# Callback: 後一天按鈕
@callback(
    Output("date-picker", "date", allow_duplicate=True),
    Input("btn-next-day", "n_clicks"),
    State("date-picker", "date"),
    prevent_initial_call=True,
)
def go_next_day(n_clicks, current_date):
    if n_clicks is None or current_date is None:
        return dash.no_update

    current = datetime.strptime(current_date, "%Y-%m-%d")
    new_date = current + timedelta(days=1)

    # 確保不超過最大日期
    if new_date > max_date:
        new_date = max_date

    return new_date.strftime("%Y-%m-%d")


# Callback: 更新圖表
@callback(
    [
        Output("money-flow-chart", "figure"),
        Output("actual-date-display", "children"),
        Output("money-flow-summary-cards", "children"),
    ],
    [Input("date-picker", "date")],
)
def update_money_flow_chart(selected_date):
    """更新金流圖表"""
    try:
        if selected_date is None:
            selected_date = max_date.strftime("%Y-%m-%d")

        fig, actual_date, result = create_money_flow_chart(
            target_date=selected_date, top_n=100
        )

        # 日期顯示
        date_str = actual_date.strftime("%Y-%m-%d") if actual_date else "無法取得日期"

        # 統計摘要
        if actual_date is not None and not result.empty:
            total_amount = result["成交金額(億)"].sum()
            avg_amount = result["成交金額(億)"].mean()
            max_stock = result.iloc[0]

            # 建立摘要卡片 (RWD: 手機版一行一個，桌面版一行四個)
            summary_cards = [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("查詢日期", className="text-muted"),
                                        html.H4(
                                            date_str,
                                            className="mb-0",
                                            style={"fontSize": "1.2rem"},
                                        ),
                                    ]
                                )
                            ],
                            className="shadow-sm",
                        )
                    ],
                    xs=12, sm=6, md=6, lg=3,  # 🔧 RWD: 手機版全寬，平板半寬，桌面版 1/4
                    className="mb-3",
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6(
                                            "前100名總成交金額", className="text-muted"
                                        ),
                                        html.H4(
                                            f"{total_amount:,.0f} 億",
                                            className="mb-0 text-primary",
                                        ),
                                    ]
                                )
                            ],
                            className="shadow-sm",
                        )
                    ],
                    xs=12, sm=6, md=6, lg=3,  # 🔧 RWD: 手機版全寬，平板半寬，桌面版 1/4
                    className="mb-3",
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("成交金額冠軍", className="text-muted"),
                                        html.H4(
                                            f"{max_stock['顯示標籤']}",
                                            className="mb-0 text-danger",
                                            style={"fontSize": "1rem"},
                                        ),
                                    ]
                                )
                            ],
                            className="shadow-sm",
                        )
                    ],
                    xs=12, sm=6, md=6, lg=3,  # 🔧 RWD: 手機版全寬，平板半寬，桌面版 1/4
                    className="mb-3",
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("冠軍成交金額", className="text-muted"),
                                        html.H4(
                                            f"{max_stock['成交金額(億)']:.1f} 億",
                                            className="mb-0 text-warning",
                                        ),
                                    ]
                                )
                            ],
                            className="shadow-sm",
                        )
                    ],
                    xs=12, sm=6, md=6, lg=3,  # 🔧 RWD: 手機版全寬，平板半寬，桌面版 1/4
                    className="mb-3",
                ),
            ]
        else:
            summary_cards = []

        return fig, date_str, summary_cards

    except Exception as e:
        print(f"❌ 更新金流圖表錯誤: {e}")
        import traceback

        traceback.print_exc()

        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text=f"錯誤: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="red"),
        )
        return empty_fig, "錯誤", []


# Callback: 更新連續進榜統計表
@callback(
    [
        Output("consecutive-ranking-table", "children"),
        Output("lookback-period-display", "children"),
    ],
    [
        Input("date-picker", "date"),
        Input("lookback-days-slider", "value"),
    ],
)
def update_consecutive_ranking_table(selected_date, lookback_days):
    """更新連續進榜統計表"""
    try:
        if selected_date is None:
            selected_date = max_date.strftime("%Y-%m-%d")

        result, trading_days = create_consecutive_ranking_table(
            target_date=selected_date,
            lookback_days=lookback_days,
            top_n=20,
        )

        # 期間顯示
        if len(trading_days) > 0:
            start_day = trading_days[0]
            end_day = trading_days[-1]
            period_str = f"{start_day.strftime('%Y-%m-%d')} ~ {end_day.strftime('%Y-%m-%d')} (共 {len(trading_days)} 個交易日)"
        else:
            period_str = "無資料"

        if result.empty:
            return (
                html.Div("無資料", className="text-muted text-center p-4"),
                period_str,
            )

        # 只顯示需要的欄位
        display_df = result[
            [
                "排名",
                "股票代號",
                "股票名稱",
                "進榜成值前20名累積天數",
                "最新成交金額(億)",
            ]
        ].copy()

        # 格式化成交金額
        display_df["最新成交金額(億)"] = display_df["最新成交金額(億)"].apply(
            lambda x: f"{x:.2f}" if x > 0 else "-"
        )

        # 建立表格
        table = dbc.Table.from_dataframe(
            display_df.head(50),  # 只顯示前 50 名
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table-sm",
        )

        return table, period_str

    except Exception as e:
        print(f"❌ 更新連續進榜統計表錯誤: {e}")
        import traceback

        traceback.print_exc()

        return html.Div(f"錯誤: {str(e)}", className="text-danger"), "錯誤"
