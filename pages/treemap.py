import dash
from dash import html, dcc, callback, Output, Input
import pandas as pd
from finlab.plot import plot_tw_stock_treemap

# 註冊頁面
dash.register_page(__name__, path="/treemap", name="產業分類圖")

# 初始化日期
today = pd.Timestamp.now().strftime("%Y-%m-%d")
yesterday = (pd.Timestamp.now() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
start_day = (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
# 頁面布局
layout = html.Div(
    [
        html.H1("台股產業塊圖", style={"marginBottom": "30px"}),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("開始日期:", style={"fontWeight": "bold"}),
                        dcc.DatePickerSingle(
                            id="treemap-start-date",
                            date=start_day,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    style={"marginRight": "20px"},
                ),
                html.Div(
                    [
                        html.Label("結束日期:", style={"fontWeight": "bold"}),
                        dcc.DatePickerSingle(
                            id="treemap-end-date",
                            date=yesterday,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    style={"marginRight": "20px"},
                ),
                html.Div(
                    [
                        html.Label("面積指標:", style={"fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="area-ind-selector",
                            options=[
                                {
                                    "label": "市值 (Market Value)",
                                    "value": "market_value",
                                },
                                {
                                    "label": "交易金額 (Turnover)",
                                    "value": "turnover",
                                },
                            ],
                            value="turnover",
                            style={"width": "250px"},
                            clearable=False,
                        ),
                    ],
                    style={"marginRight": "20px"},
                ),
                html.Div(
                    [
                        html.Label("顯示項目:", style={"fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="item-selector",
                            options=[
                                {
                                    "label": "報酬率 (Return Ratio)",
                                    "value": "return_ratio",
                                },
                                {
                                    "label": "月營收年增率 (Monthly yoy)",
                                    "value": "monthly_revenue:去年同月增減(%)",
                                },
                                {
                                    "label": "本益比 (PE Ratio)",
                                    "value": "price_earning_ratio:本益比",
                                },
                            ],
                            value="return_ratio",
                            style={"width": "250px"},
                            clearable=False,
                        ),
                    ],
                    style={"marginRight": "20px"},
                ),
                html.Button(
                    "🔄 更新圖表",
                    id="treemap-refresh-btn",
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
        # 進階選項 (可展開/收合)
        html.Details(
            [
                html.Summary(
                    "進階選項",
                    style={
                        "cursor": "pointer",
                        "fontWeight": "bold",
                        "marginBottom": "10px",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label(
                                    "色溫條樣式:",
                                    style={"fontWeight": "bold", "marginRight": "10px"},
                                ),
                                dcc.Dropdown(
                                    id="color-continuous-scale-selector",
                                    options=[
                                        {"label": "Temps (預設)", "value": "Temps"},
                                        {"label": "RdYlGn", "value": "RdYlGn"},
                                        {"label": "RdBu_r", "value": "RdBu_r"},
                                        {"label": "Viridis", "value": "Viridis"},
                                        {"label": "Plasma", "value": "Plasma"},
                                        {"label": "Blues", "value": "Blues"},
                                        {"label": "Reds", "value": "Reds"},
                                        {"label": "Greens", "value": "Greens"},
                                    ],
                                    value="Temps",
                                    style={"width": "200px"},
                                    clearable=False,
                                ),
                            ],
                            style={"display": "inline-block", "marginRight": "20px"},
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "數值限定範圍 (Clip):",
                                    style={"fontWeight": "bold", "marginRight": "10px"},
                                ),
                                dcc.Input(
                                    id="clip-min",
                                    type="number",
                                    placeholder="最小值",
                                    value=0,
                                    style={"width": "100px", "marginRight": "10px"},
                                ),
                                html.Span("~", style={"marginRight": "10px"}),
                                dcc.Input(
                                    id="clip-max",
                                    type="number",
                                    placeholder="最大值",
                                    value=200,
                                    style={"width": "100px"},
                                ),
                            ],
                            style={"display": "inline-block", "marginRight": "20px"},
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "使用還原股價:",
                                    style={"fontWeight": "bold", "marginRight": "10px"},
                                ),
                                dcc.Checklist(
                                    id="adjust-price-checkbox",
                                    options=[{"label": "", "value": "adjust"}],
                                    value=[],
                                    style={"display": "inline-block"},
                                ),
                            ],
                            style={"display": "inline-block"},
                        ),
                    ],
                    style={
                        "padding": "10px",
                        "backgroundColor": "#f8f9fa",
                        "borderRadius": "5px",
                    },
                ),
            ],
            style={"marginBottom": "20px"},
        ),
        # 載入提示
        dcc.Loading(
            id="loading-treemap",
            type="default",
            children=[html.Div(id="treemap-container", style={"minHeight": "600px"})],
        ),
    ],
    style={"padding": "20px"},
)


@callback(
    Output("treemap-container", "children"),
    [
        Input("treemap-start-date", "date"),
        Input("treemap-end-date", "date"),
        Input("area-ind-selector", "value"),
        Input("item-selector", "value"),
        Input("color-continuous-scale-selector", "value"),
        Input("clip-min", "value"),
        Input("clip-max", "value"),
        Input("adjust-price-checkbox", "value"),
        Input("treemap-refresh-btn", "n_clicks"),
    ],
)
def update_treemap(
    start_date,
    end_date,
    area_ind,
    item,
    color_continuous_scale,
    clip_min,
    clip_max,
    adjust_price,
    n_clicks,
):
    try:
        # 檢查日期有效性
        if not start_date or not end_date:
            return html.Div(
                [
                    html.P(
                        "請選擇開始和結束日期",
                        style={"color": "red", "textAlign": "center"},
                    )
                ]
            )

        # 設定 clip 範圍
        clip = None
        if clip_min is not None and clip_max is not None:
            clip = (clip_min, clip_max)

        # 判斷是否使用還原股價
        adjust = "adjust" in adjust_price if adjust_price else False

        # 生成樹狀圖
        fig = plot_tw_stock_treemap(
            start=start_date,
            end=end_date,
            area_ind=area_ind,
            item=item,
            color_continuous_scale=color_continuous_scale,
            clip=clip,
        )

        # 返回圖表
        return dcc.Graph(
            figure=fig,
            style={"height": "600px"},
            config={"displayModeBar": True, "displaylogo": False},
        )

    except Exception as e:
        return html.Div(
            [
                html.H4("❌ 圖表生成錯誤", style={"color": "red"}),
                html.P(f"錯誤訊息: {str(e)}"),
                html.P("請檢查日期範圍和參數設定是否正確", style={"color": "gray"}),
            ],
            style={"textAlign": "center", "padding": "50px"},
        )
