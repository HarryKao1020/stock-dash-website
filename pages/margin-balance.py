import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# 從 finlab_data 模組匯入資料
from finlab_data import finlab_data

# 註冊頁面
dash.register_page(__name__, path="/margin-balance", name="融資餘額")


def create_margin_figure(start_date, end_date):
    """建立融資維持率圖表"""
    try:
        # 從 finlab_data 取得資料
        融資維持率, 融資券總餘額, benchmark, close = finlab_data.get_margin_data()

        # 篩選日期範圍
        df = 融資維持率.loc[
            (融資維持率.index >= start_date) & (融資維持率.index <= end_date)
        ]
        df2 = 融資券總餘額.loc[
            (融資券總餘額.index >= start_date) & (融資券總餘額.index <= end_date)
        ]

    except Exception as e:
        print(f"❌ 取得融資資料錯誤: {e}")
        # 回傳空白圖表
        fig = go.Figure()
        fig.add_annotation(
            text=f"無法取得資料: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="red"),
        )
        return fig

    # 建立子圖
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        specs=[
            [{"secondary_y": True}],
            [{"secondary_y": True}],
            [{"secondary_y": True}],
        ],
        subplot_titles=("融資維持率", "上市融資餘額", "上櫃融資餘額"),
    )

    date_index = df.index
    benchmark_values = benchmark.reindex(df.index)

    # ========== 第一張圖: 融資維持率 ==========
    # 大盤加權報酬指數
    fig.add_trace(
        go.Scatter(
            x=date_index,
            y=benchmark_values,
            name="大盤加權報酬指數",
            line=dict(width=3, color="#1f77b4"),
        ),
        secondary_y=False,
        row=1,
        col=1,
    )

    # 融資維持率
    fig.add_trace(
        go.Scatter(
            x=date_index, y=df.values, name="融資維持率", line=dict(color="#ff7f0e")
        ),
        secondary_y=True,
        row=1,
        col=1,
    )

    # 融資維持率 10日均線
    fig.add_trace(
        go.Scatter(
            x=date_index,
            y=df.rolling(10).mean().values,
            name="融資維持率_MA10",
            line=dict(color="#2ca02c", dash="dash"),
        ),
        secondary_y=True,
        row=1,
        col=1,
    )

    # ========== 第二張圖: 上市融資 ==========
    # 上市融資餘額
    fig.add_trace(
        go.Scatter(
            x=date_index,
            y=df2["上市融資交易金額"],
            fill="tozeroy",
            line=dict(width=0.5, color="#efd267"),
            name="上市融資餘額",
        ),
        secondary_y=False,
        row=2,
        col=1,
    )

    # 上市融資買賣超
    colors = ["red" if x > 0 else "green" for x in df2["上市融資買賣超"]]
    fig.add_trace(
        go.Bar(
            x=date_index,
            y=df2["上市融資買賣超"],
            marker_color=colors,
            name="上市融資買賣超",
        ),
        secondary_y=True,
        row=2,
        col=1,
    )

    # ========== 第三張圖: 上櫃融資 ==========
    # 上櫃融資餘額
    fig.add_trace(
        go.Scatter(
            x=date_index,
            y=df2["上櫃融資交易金額"],
            fill="tozeroy",
            line=dict(width=0.5, color="#efd267"),
            name="上櫃融資餘額",
        ),
        secondary_y=False,
        row=3,
        col=1,
    )

    # 上櫃融資買賣超
    colors = ["red" if x > 0 else "green" for x in df2["上櫃融資買賣超"]]
    fig.add_trace(
        go.Bar(
            x=date_index,
            y=df2["上櫃融資買賣超"],
            marker_color=colors,
            name="上櫃融資買賣超",
        ),
        secondary_y=True,
        row=3,
        col=1,
    )

    # 移除假日空值
    dt_all = pd.date_range(start=date_index.values[0], end=date_index.values[-1])
    dt_obs = [d.strftime("%Y-%m-%d") for d in pd.to_datetime(close.index)]
    dt_breaks = [d for d in dt_all.strftime("%Y-%m-%d").tolist() if d not in dt_obs]
    fig.update_xaxes(rangebreaks=[dict(values=dt_breaks)])

    # ========== Layout 設定 ==========
    fig.update_layout(
        height=800,
        title={
            "text": "台股大盤融資餘額分析",
            "font": {"size": 24, "color": "navy"},
            "x": 0.5,
            "xanchor": "center",
        },
        hovermode="x unified",
        showlegend=True,
        # Y軸設定
        yaxis=dict(title="指數", showgrid=False),
        yaxis2=dict(title="融資維持率"),
        yaxis3=dict(title="餘額(元)", showgrid=False),
        yaxis4=dict(title="買賣超(億)"),
        yaxis5=dict(title="餘額(元)", showgrid=False),
        yaxis6=dict(title="買賣超(億)"),
        # X軸設定 - 第三個子圖加入 rangeslider
        xaxis3=dict(rangeslider=dict(visible=True), type="date"),
    )

    return fig


# ========== 頁面佈局 ==========
layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("📊 融資餘額分析", className="mb-4 text-primary"),
                        html.Hr(),
                    ],
                    width=12,
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "📅 日期範圍選擇", className="card-title"
                                        ),
                                        # 快速選擇按鈕
                                        html.Label(
                                            "快速選擇:", className="fw-bold mb-2"
                                        ),
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    "1個月",
                                                    id="btn-1m",
                                                    size="sm",
                                                    outline=True,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "3個月",
                                                    id="btn-3m",
                                                    size="sm",
                                                    outline=True,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "6個月",
                                                    id="btn-6m",
                                                    size="sm",
                                                    outline=True,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "1年",
                                                    id="btn-1y",
                                                    size="sm",
                                                    outline=True,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "3年",
                                                    id="btn-3y",
                                                    size="sm",
                                                    outline=True,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "全部",
                                                    id="btn-all",
                                                    size="sm",
                                                    outline=True,
                                                    color="primary",
                                                ),
                                            ],
                                            className="mb-3 d-flex flex-wrap",
                                        ),
                                        html.Hr(),
                                        # 日期選擇器
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "開始日期:",
                                                            className="fw-bold",
                                                        ),
                                                        dcc.DatePickerSingle(
                                                            id="margin-start-date",
                                                            date=(
                                                                datetime.now()
                                                                - timedelta(days=365)
                                                            ).strftime("%Y-%m-%d"),
                                                            display_format="YYYY-MM-DD",
                                                            className="mb-2",
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "結束日期:",
                                                            className="fw-bold",
                                                        ),
                                                        dcc.DatePickerSingle(
                                                            id="margin-end-date",
                                                            date=datetime.now().strftime(
                                                                "%Y-%m-%d"
                                                            ),
                                                            display_format="YYYY-MM-DD",
                                                            className="mb-2",
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                            ]
                                        ),
                                        dbc.Button(
                                            "🔄 更新圖表",
                                            id="margin-update-btn",
                                            color="primary",
                                            className="mt-3 w-100",
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
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Loading(
                            id="margin-loading",
                            type="default",
                            children=[
                                dcc.Graph(
                                    id="margin-chart",
                                    config={
                                        "displayModeBar": True,
                                        "displaylogo": False,
                                        "modeBarButtonsToRemove": [
                                            "lasso2d",
                                            "select2d",
                                        ],
                                    },
                                )
                            ],
                        )
                    ],
                    width=12,
                )
            ]
        ),
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
                                                        html.Strong("融資維持率"),
                                                        ": 融資餘額市值 / 融資總金額,正常水位為 1.67,低於 1.50 表示籌碼不穩",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("融資維持率 MA10"),
                                                        ": 10日移動平均線,當融資維持率突破 MA10 時,多方籌碼開始凝聚",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("融資買賣超"),
                                                        ": 紅色代表買超,綠色代表賣超,持續賣超代表浮動籌碼被洗出",
                                                    ]
                                                ),
                                                html.Li(
                                                    [
                                                        html.Strong("觀察重點"),
                                                        ": 融資維持率低檔 + 融資賣超持續 → 可能接近底部;融資維持率突破 MA10 → 籌碼轉強訊號",
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
)


# ========== Callback: 快速日期選擇 ==========
@callback(
    [Output("margin-start-date", "date"), Output("margin-end-date", "date")],
    [
        Input("btn-1m", "n_clicks"),
        Input("btn-3m", "n_clicks"),
        Input("btn-6m", "n_clicks"),
        Input("btn-1y", "n_clicks"),
        Input("btn-3y", "n_clicks"),
        Input("btn-all", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def update_date_range(btn_1m, btn_3m, btn_6m, btn_1y, btn_3y, btn_all):
    """根據按鈕更新日期範圍"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    end_date = datetime.now().strftime("%Y-%m-%d")

    days_map = {
        "btn-1m": 30,
        "btn-3m": 90,
        "btn-6m": 180,
        "btn-1y": 365,
        "btn-3y": 365 * 3,
        "btn-all": 365 * 10,  # 10年資料
    }

    days = days_map.get(button_id, 365)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    return start_date, end_date


# ========== Callback: 更新圖表 ==========
@callback(
    Output("margin-chart", "figure"),
    [Input("margin-update-btn", "n_clicks")],
    [State("margin-start-date", "date"), State("margin-end-date", "date")],
)
def update_chart(n_clicks, start_date, end_date):
    """更新圖表"""
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    return create_margin_figure(start_date, end_date)
