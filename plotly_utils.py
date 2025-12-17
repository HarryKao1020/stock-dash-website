"""
Plotly 圖表工具函數
提供統一的暗黑模式支持
"""

def get_plotly_layout_template(is_dark_mode=False):
    """
    取得 Plotly layout 的基礎配置

    Args:
        is_dark_mode: 是否為暗黑模式

    Returns:
        dict: layout 配置
    """
    if is_dark_mode:
        return {
            'plot_bgcolor': 'rgba(20, 20, 20, 0.95)',
            'paper_bgcolor': 'rgba(20, 20, 20, 0.95)',
            'font': {'color': '#f5f5f5'},
            'xaxis': {
                'gridcolor': 'rgba(255, 255, 255, 0.1)',
                'tickfont': {'color': '#f5f5f5'},
                'titlefont': {'color': '#f5f5f5'}
            },
            'yaxis': {
                'gridcolor': 'rgba(255, 255, 255, 0.1)',
                'tickfont': {'color': '#f5f5f5'},
                'titlefont': {'color': '#f5f5f5'}
            },
            'hoverlabel': {
                'bgcolor': 'rgba(30, 30, 30, 0.95)',
                'font': {'color': '#f5f5f5'}
            },
            'legend': {
                'font': {'color': '#f5f5f5'}
            }
        }
    else:
        return {
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'font': {'color': '#333'},
            'xaxis': {
                'gridcolor': 'rgba(128,128,128,0.2)',
                'tickfont': {'color': '#333'},
            },
            'yaxis': {
                'gridcolor': 'rgba(128,128,128,0.2)',
                'tickfont': {'color': '#333'},
            },
            'hoverlabel': {
                'bgcolor': 'white',
            },
            'legend': {
                'font': {'color': '#333'}
            }
        }


def apply_dark_mode_to_figure(fig):
    """
    在前端透過 CSS 自動應用暗黑模式樣式

    此函數確保圖表使用透明背景，讓 CSS 能夠控制顏色
    """
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig
