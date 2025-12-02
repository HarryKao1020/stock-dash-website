"""
市值成長分析模組
分析指定期間內市值的成長率與排名變化
"""

import pandas as pd
import numpy as np
from finlab import data


def get_stock_names(stock_list):
    """
    取得股票代碼對應的公司簡稱和產業類別

    參數:
    stock_list (list): 股票代碼列表

    返回:
    tuple: (公司簡稱字典, 產業類別字典)
    """
    company_info = data.get("company_basic_info")
    result = company_info.loc[
        company_info["stock_id"].isin(stock_list), ["stock_id", "公司簡稱", "產業類別"]
    ]
    result_indexed = result.set_index("stock_id")
    result_ordered = result_indexed.reindex(stock_list)

    # 回傳公司簡稱和產業類別的字典
    names_dict = result_ordered["公司簡稱"].to_dict()
    industry_dict = result_ordered["產業類別"].to_dict()

    return names_dict, industry_dict


def analyze_market_value_growth(top_n=100, days=30, market_value=None):
    """
    分析市值成長率與排名變化

    參數:
    top_n (int): 分析目前市值前 N 名的股票,預設 100
    days (int): 分析期間天數,預設 30 天
    market_value (DataFrame): 市值資料,如果為 None 則自動取得

    返回:
    DataFrame: 包含股票代號、公司名稱、排名變化、市值成長率等資訊
    """
    # 取得市值資料
    if market_value is None:
        print("正在載入市值資料...")
        market_value = data.get("etl:market_value")

    # 確認資料長度足夠
    if len(market_value) < days:
        raise ValueError(f"市值資料不足 {days} 天,目前只有 {len(market_value)} 天")

    # 取得最新日期和 N 天前的日期
    latest_date = market_value.index[-1]
    past_date = market_value.index[-days - 1]  # -days-1 因為要包含當天

    print(
        f"分析期間: {past_date.strftime('%Y-%m-%d')} 至 {latest_date.strftime('%Y-%m-%d')}"
    )

    # 取得最新一天的市值前 top_n 名
    latest_data = market_value.loc[latest_date].dropna()
    latest_rank = latest_data.sort_values(ascending=False)
    top_stocks = latest_rank.head(top_n).index.tolist()

    print(f"正在分析前 {top_n} 名股票的市值成長...")

    # 取得過去的市值資料
    past_data = market_value.loc[past_date]

    # 建立結果列表
    results = []

    for stock in top_stocks:
        # 現在的市值和排名
        current_value = latest_data[stock]
        current_rank = (latest_rank >= current_value).sum()

        # 過去的市值和排名
        if stock in past_data.index and not pd.isna(past_data[stock]):
            past_value = past_data[stock]
            past_rank_series = past_data.sort_values(ascending=False)
            past_rank = (past_rank_series >= past_value).sum()

            # 計算成長率
            growth_rate = ((current_value - past_value) / past_value) * 100

            # 排名變化 (正數表示進步,往前爬)
            rank_change = past_rank - current_rank
        else:
            # 如果過去沒有資料,標記為新進榜
            past_value = np.nan
            past_rank = np.nan
            growth_rate = np.nan
            rank_change = np.nan

        results.append(
            {
                "股票代號": stock,
                f"{days}天前市值(億)": (
                    past_value / 1e8 if not pd.isna(past_value) else np.nan
                ),
                f"{days}天前排名": past_rank if not pd.isna(past_rank) else "-",
                "目前市值(億)": current_value / 1e8,
                "目前排名": current_rank,
                "排名變化": rank_change if not pd.isna(rank_change) else "-",
                "市值成長率(%)": growth_rate,
            }
        )

    # 轉換為 DataFrame
    df = pd.DataFrame(results)

    # 取得公司名稱和產業類別
    print("正在取得公司名稱和產業類別...")
    stock_names, stock_industries = get_stock_names(top_stocks)
    df["公司名稱"] = df["股票代號"].map(stock_names)
    df["產業類別"] = df["股票代號"].map(stock_industries)

    # 調整欄位順序
    columns_order = [
        "股票代號",
        "公司名稱",
        "產業類別",
        f"{days}天前排名",
        "目前排名",
        "排名變化",
        f"{days}天前市值(億)",
        "目前市值(億)",
        "市值成長率(%)",
    ]
    df = df[columns_order]

    # 依照市值成長率排序 (由高到低)
    df = df.sort_values("市值成長率(%)", ascending=False, na_position="last")

    # 重設索引
    df = df.reset_index(drop=True)

    # 格式化數值顯示
    df[f"{days}天前市值(億)"] = df[f"{days}天前市值(億)"].apply(
        lambda x: f"{x:,.0f}" if not pd.isna(x) else "-"
    )
    df["目前市值(億)"] = df["目前市值(億)"].apply(lambda x: f"{x:,.0f}")
    df["市值成長率(%)"] = df["市值成長率(%)"].apply(
        lambda x: f"{x:+.2f}%" if not pd.isna(x) else "-"
    )

    return df


def get_top_growth_stocks(top_n=100, days=30, result_n=20):
    """
    取得市值成長率最高的前 N 支股票

    參數:
    top_n (int): 從目前市值前 N 名中篩選,預設 100
    days (int): 分析期間天數,預設 30 天
    result_n (int): 回傳前 N 名成長股,預設 20

    返回:
    DataFrame: 市值成長率最高的股票清單
    """
    df = analyze_market_value_growth(top_n=top_n, days=days)
    return df.head(result_n)


def get_top_rank_climbers(top_n=100, days=30, result_n=20):
    """
    取得排名爬升最多的股票

    參數:
    top_n (int): 從目前市值前 N 名中篩選,預設 100
    days (int): 分析期間天數,預設 30 天
    result_n (int): 回傳前 N 名,預設 20

    返回:
    DataFrame: 排名爬升最多的股票清單
    """
    df = analyze_market_value_growth(top_n=top_n, days=days)

    # 將排名變化轉換為數值 (排除 '-')
    df_copy = df.copy()
    df_copy["排名變化_數值"] = pd.to_numeric(
        df_copy["排名變化"].replace("-", np.nan), errors="coerce"
    )

    # 依照排名變化排序 (由高到低,正數表示排名上升)
    df_sorted = df_copy.sort_values(
        "排名變化_數值", ascending=False, na_position="last"
    )

    # 移除臨時欄位
    df_sorted = df_sorted.drop("排名變化_數值", axis=1)

    return df_sorted.head(result_n)


def print_growth_analysis(df, title="市值成長分析"):
    """
    格式化印出分析結果

    參數:
    df (DataFrame): 分析結果 DataFrame
    title (str): 標題
    """
    print("\n" + "=" * 100)
    print(f"{title:^100}")
    print("=" * 100)
    print(df.to_string(index=True))
    print("=" * 100)


def save_to_excel(df, filename="market_value_growth.xlsx"):
    """
    將分析結果儲存為 Excel 檔案

    參數:
    df (DataFrame): 分析結果 DataFrame
    filename (str): 檔案名稱
    """
    df.to_excel(filename, index=False)
    print(f"已儲存至 {filename}")


if __name__ == "__main__":
    # 測試用
    print("市值成長分析範例...")
    df = analyze_market_value_growth(top_n=50, days=30)
    print_growth_analysis(df.head(20), "市值成長率前 20 名")
