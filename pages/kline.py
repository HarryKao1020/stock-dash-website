import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
from finlab import data
from datetime import datetime, timedelta

# 從 finlab_data.py 匯入
import sys

sys.path.append("..")  # 如果 finlab_data.py 在上層目錄
from finlab_data import finlab_data

# 註冊頁面
dash.register_page(__name__, path="/kline", name="K線圖")

# 啟動時載入資料
print("📊 初始化 FinLab 資料...")
# 取得股票列表
stock_list = finlab_data.get_stock_list()


# 頁面布局
layout = dbc.Container(
    [
        # 標題區
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("📈 個股K線圖", className="mb-3 text-primary"),
                        html.P(
                            "查看個股K線走勢與技術分析指標",
                            className="text-muted",
                        ),
                        html.Hr(),
                    ],
                    width=12,
                )
            ]
        ),
        # 控制面板
        html.Div(
            [
                html.Div(
                    [
                        html.Label("選擇股票:", style={"fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="stock-selector",
                            options=[
                                {
                                    "label": stock,
                                    "value": stock.split()[0],
                                }  # label 顯示完整, value 只取代號
                                for stock in stock_list
                            ],
                            value="2330",
                            style={"width": "300px"},  # 寬度加大以容納名稱
                        ),
                    ],
                    style={"marginRight": "20px"},
                ),
                html.Div(
                    [
                        html.Label("日期範圍:", style={"fontWeight": "bold"}),
                        dcc.DatePickerRange(
                            id="date-range",
                            start_date=(datetime.now() - timedelta(days=120)).strftime(
                                "%Y-%m-%d"
                            ),
                            end_date=pd.Timestamp.now().strftime("%Y-%m-%d"),
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    style={"marginRight": "20px"},
                ),
                html.Button(
                    "🔄 更新資料",
                    id="refresh-btn",
                    n_clicks=0,
                    className="btn btn-primary",
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "flex-end",
                "marginBottom": "30px",
                "flexWrap": "wrap",
                "gap": "10px",
            },
        ),
        # K線圖和成交量合併在一起
        dcc.Graph(
            id="candlestick-chart", style={"height": "800px", "marginBottom": "20px"}
        ),
        # 統計資訊
        html.Div(
            id="stats-info", className="card p-3", style={"backgroundColor": "#f8f9fa"}
        ),
    ],
    fluid=True,
    className="p-4",
)


@callback(
    [
        Output("candlestick-chart", "figure"),
        Output("stats-info", "children"),
    ],
    [
        Input("stock-selector", "value"),
        Input("date-range", "start_date"),
        Input("date-range", "end_date"),
        Input("refresh-btn", "n_clicks"),
    ],
)
def update_charts(stock_id, start_date, end_date, n_clicks):

    # 如果按了更新按鈕,重新載入資料
    if n_clicks > 0:
        finlab_data.refresh()

    # 從 finlab_data 取得資料
    df = finlab_data.get_stock_data(stock_id, start_date, end_date)

    # 確保索引是 datetime 格式
    df.index = pd.to_datetime(df.index)

    # 移除無效資料 - 更嚴格的篩選
    df = df.dropna(subset=["open", "high", "low", "close", "volume"])
    df = df[(df["volume"] > 0)]

    # 重置索引以確保資料完整性
    df = df.copy()

    # 檢查是否有資料
    if len(df) == 0:
        # 如果沒有資料,返回空圖表
        fig = go.Figure()
        fig.add_annotation(
            text="查無資料",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20),
        )
        stats = html.Div([html.P("查無資料")])
        return fig, stats

    # 計算移動平均線
    df["MA5"] = df["close"].rolling(window=5).mean()
    df["MA10"] = df["close"].rolling(window=10).mean()
    df["MA20"] = df["close"].rolling(window=20).mean()
    df["MA60"] = df["close"].rolling(window=60).mean()
    df["MA120"] = df["close"].rolling(window=120).mean()
    df.index = df.index.strftime("%Y-%m-%d")
    # 成交量顏色(紅跌綠漲)
    colors = []
    for i in range(len(df)):
        try:
            if float(df["close"].iloc[i]) < float(df["open"].iloc[i]):
                colors.append("red")
            else:
                colors.append("green")
        except:
            colors.append("gray")

    # 建立子圖(K線在上,成交量在下)
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{stock_id}股價走勢", "成交量"),  # 加入股票名稱
    )

    # 加入K線圖
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K線",
            increasing_line_color="red",
            decreasing_line_color="green",
        ),
        row=1,
        col=1,
    )

    # 加入移動平均線
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA5"],
            name="MA5",
            line=dict(color="purple", width=1.5),
            mode="lines",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA10"],
            name="MA10",
            line=dict(color="blue", width=1.5),
            mode="lines",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA20"],
            name="MA20",
            line=dict(color="orange", width=1.5),
            mode="lines",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA60"],
            name="MA60",
            line=dict(color="brown", width=1.5),
            mode="lines",
        ),
        row=1,
        col=1,
    ),
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA120"],
            name="MA120",
            line=dict(color="brown", width=1.5),
            mode="lines",
        ),
        row=1,
        col=1,
    )

    # 加入成交量圖
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["volume"],
            name="成交量",
            marker_color=colors,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # 更新布局
    fig.update_layout(
        title=f"{stock_id} 技術分析",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=800,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # 移除假日空白 - 使用 type='category'
    fig.update_xaxes(type="category", tickformat="%Y-%m-%d", row=1, col=1)

    fig.update_xaxes(
        type="category", tickformat="%Y-%m-%d", title_text="日期", row=2, col=1
    )

    # 更新 Y 軸標籤
    fig.update_yaxes(title_text="價格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)

    # 統計資訊 - 加上錯誤處理
    try:
        latest_close = float(df["close"].iloc[-1])
        max_high = float(df["high"].max())
        min_low = float(df["low"].min())
        avg_volume = float(df["volume"].mean())
        data_count = len(df)

        # 加入最新 MA 值
        latest_ma5 = df["MA5"].iloc[-1] if pd.notna(df["MA5"].iloc[-1]) else None
        latest_ma10 = df["MA10"].iloc[-1] if pd.notna(df["MA10"].iloc[-1]) else None
        latest_ma20 = df["MA20"].iloc[-1] if pd.notna(df["MA20"].iloc[-1]) else None
        latest_ma60 = df["MA60"].iloc[-1] if pd.notna(df["MA60"].iloc[-1]) else None
        latest_ma120 = df["MA120"].iloc[-1] if pd.notna(df["MA120"].iloc[-1]) else None

        stats = html.Div(
            [
                html.H3("📈 統計資訊", className="mb-3"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Strong("最新收盤價: "),
                                html.Span(
                                    f"{latest_close:.2f}",
                                    style={"fontSize": "18px", "color": "#0d6efd"},
                                ),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Strong("期間最高價: "),
                                html.Span(f"{max_high:.2f}", style={"color": "green"}),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Strong("期間最低價: "),
                                html.Span(f"{min_low:.2f}", style={"color": "red"}),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Strong("平均成交量: "),
                                html.Span(f"{avg_volume:,.0f}"),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [html.Strong("資料筆數: "), html.Span(f"{data_count}")],
                            className="mb-2",
                        ),
                        html.Hr(),
                        html.H5("移動平均線", className="mt-3 mb-2"),
                        html.Div(
                            [
                                html.Span(
                                    "MA5: ",
                                    style={"fontWeight": "bold", "color": "purple"},
                                ),
                                html.Span(
                                    f"{latest_ma5:.2f}" if latest_ma5 else "N/A",
                                    style={"marginRight": "15px"},
                                ),
                                html.Span(
                                    "MA10: ",
                                    style={"fontWeight": "bold", "color": "blue"},
                                ),
                                html.Span(
                                    f"{latest_ma10:.2f}" if latest_ma10 else "N/A",
                                    style={"marginRight": "15px"},
                                ),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Span(
                                    "MA20: ",
                                    style={"fontWeight": "bold", "color": "orange"},
                                ),
                                html.Span(
                                    f"{latest_ma20:.2f}" if latest_ma20 else "N/A",
                                    style={"marginRight": "15px"},
                                ),
                                html.Span(
                                    "MA60: ",
                                    style={"fontWeight": "bold", "color": "brown"},
                                ),
                                html.Span(
                                    f"{latest_ma60:.2f}" if latest_ma60 else "N/A"
                                ),
                            ]
                        ),
                    ]
                ),
            ]
        )
    except Exception as e:
        stats = html.Div(
            [
                html.H3("📈 統計資訊", className="mb-3"),
                html.P(f"統計資料計算錯誤: {str(e)}", style={"color": "red"}),
            ]
        )

    return fig, stats
