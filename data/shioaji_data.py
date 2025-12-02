"""
Shioaji API 資料處理模組
用於取得台股加權指數和櫃買指數的即時資料
"""

import pandas as pd
import numpy as np
import talib
from datetime import datetime, date
from pathlib import Path
import pickle


# 快取目錄設定
CACHE_DIR = Path(__file__).parent / "cache" / "shioaji"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_index_with_macd(api, index_type="TSE", start="2024-10-01", end="2025-12-01"):
    """
    取得指數日線 + MACD + 均線
    """
    # 選擇合約
    contract = (
        api.Contracts.Indexs.TSE.TSE001
        if index_type == "TSE"
        else api.Contracts.Indexs.OTC.OTC101
    )

    # 取得並處理資料
    kbars = api.kbars(contract=contract, start=start, end=end)
    df = pd.DataFrame(kbars.model_dump())
    df["ts"] = pd.to_datetime(df["ts"])
    df["date"] = df["ts"].dt.date

    # 轉日線
    daily = df.groupby("date").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Amount": "sum"}
    )

    daily.index = pd.to_datetime(daily.index)
    daily["Volume"] = daily["Amount"] / 1e8

    # 計算 MACD
    daily["DIF"], daily["MACD"], daily["MACD_Hist"] = talib.MACD(
        daily["Close"].values, fastperiod=12, slowperiod=26, signalperiod=9
    )

    # 計算均線
    daily["ma5"] = daily["Close"].rolling(window=5).mean().round(2)
    daily["ma20"] = daily["Close"].rolling(window=20).mean().round(2)
    daily["ma60"] = daily["Close"].rolling(window=60).mean().round(2)
    daily["ma120"] = daily["Close"].rolling(window=120).mean().round(2)

    return daily[
        [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "DIF",
            "MACD",
            "MACD_Hist",
            "ma5",
            "ma20",
            "ma60",
            "ma120",
        ]
    ]


def update_both_indexes_realtime(tse_df, otc_df, api, use_cache=True):
    """
    同時更新 TSE 和 OTC (1分鐘更新優化版) + 均線計算
    """

    contracts = [api.Contracts.Indexs.TSE.TSE001, api.Contracts.Indexs.OTC.OTC101]

    try:
        snapshots = api.snapshots(contracts)
    except Exception as e:
        print(f"API 呼叫失敗: {e}")
        return tse_df, otc_df

    def update_single_df(daily_df, snapshot):
        today = pd.Timestamp(datetime.fromtimestamp(snapshot.ts / 1e9).date())

        # 檢查是否為新的一天
        is_new_day = today not in daily_df.index

        if is_new_day:
            # 新增當天資料
            daily_df.loc[today] = {
                "Open": snapshot.open,
                "High": snapshot.high,
                "Low": snapshot.low,
                "Close": snapshot.close,
                "Volume": snapshot.total_amount / 1e8,
                "Amount": snapshot.total_amount,
                "DIF": np.nan,
                "MACD": np.nan,
                "MACD_Hist": np.nan,
                "ma5": np.nan,
                "ma20": np.nan,
                "ma60": np.nan,
                "ma120": np.nan,
            }
        else:
            # 更新當天資料
            daily_df.loc[today, "Open"] = snapshot.open
            daily_df.loc[today, "High"] = max(
                daily_df.loc[today, "High"], snapshot.high
            )
            daily_df.loc[today, "Low"] = min(daily_df.loc[today, "Low"], snapshot.low)
            daily_df.loc[today, "Close"] = snapshot.close
            daily_df.loc[today, "Volume"] = snapshot.total_amount / 1e8

        # 計算 MACD - 只取必要的資料長度
        window_size = 50
        if len(daily_df) >= window_size:
            recent_data = daily_df.tail(window_size)
        else:
            recent_data = daily_df

        macd_dif, macd_signal, macd_hist = talib.MACD(
            recent_data["Close"].values, fastperiod=12, slowperiod=26, signalperiod=9
        )

        # 只更新今天的 MACD 值
        if not np.isnan(macd_dif[-1]):
            daily_df.loc[today, "DIF"] = macd_dif[-1]
            daily_df.loc[today, "MACD"] = macd_signal[-1]
            daily_df.loc[today, "MACD_Hist"] = macd_hist[-1]

        # 計算均線 - 使用 rolling 方式更有效率
        # ma5
        if len(daily_df) >= 5:
            ma5_window = daily_df["Close"].tail(5)
            daily_df.loc[today, "ma5"] = ma5_window.mean()

        # ma20
        if len(daily_df) >= 20:
            ma20_window = daily_df["Close"].tail(20)
            daily_df.loc[today, "ma20"] = ma20_window.mean()

        # ma60
        if len(daily_df) >= 60:
            ma60_window = daily_df["Close"].tail(60)
            daily_df.loc[today, "ma60"] = ma60_window.mean()

        # ma120
        if len(daily_df) >= 120:
            ma120_window = daily_df["Close"].tail(120)
            daily_df.loc[today, "ma120"] = ma120_window.mean()

        return daily_df

    tse_df = update_single_df(tse_df, snapshots[0])
    otc_df = update_single_df(otc_df, snapshots[1])

    return tse_df, otc_df


def _get_cache_path(index_type):
    """取得快取檔案路徑"""
    return CACHE_DIR / f"{index_type}_historical.pkl"


def _save_to_cache(df, index_type):
    """儲存歷史資料到快取檔案"""
    try:
        cache_path = _get_cache_path(index_type)
        # 只儲存今天之前的資料
        today = pd.Timestamp.now().normalize()
        historical_df = df[df.index < today].copy()

        with open(cache_path, "wb") as f:
            pickle.dump(historical_df, f)

        print(
            f"✅ {index_type} 歷史資料已儲存到快取 (截至 {historical_df.index.max().date()})"
        )
        return True
    except Exception as e:
        print(f"⚠️ 儲存快取失敗: {e}")
        return False


def _load_from_cache(index_type):
    """從快取檔案載入歷史資料"""
    try:
        cache_path = _get_cache_path(index_type)

        if not cache_path.exists():
            print(f"📂 找不到 {index_type} 的快取檔案")
            return None

        with open(cache_path, "rb") as f:
            df = pickle.load(f)

        print(f"✅ 從快取載入 {index_type} 歷史資料 (截至 {df.index.max().date()})")
        return df
    except Exception as e:
        print(f"⚠️ 載入快取失敗: {e}")
        return None


def _need_update_historical(cached_df):
    """檢查是否需要更新歷史資料"""
    if cached_df is None:
        return True

    # 檢查快取的最後日期
    last_date = cached_df.index.max()
    yesterday = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)

    # 如果快取資料到昨天,就不用更新
    if last_date >= yesterday:
        print(f"📊 歷史資料已是最新 (截至 {last_date.date()})")
        return False

    print(f"🔄 歷史資料需要更新 (快取: {last_date.date()}, 需要到: {yesterday.date()})")
    return True


def get_index_data_smart(
    api, index_type="TSE", start="2024-01-01", force_refresh=False
):
    """
    智慧取得指數資料 (使用快取優化)

    策略:
    1. 載入快取的歷史資料 (今天之前)
    2. 只向 API 請求缺少的日期
    3. 合併資料並更新快取
    4. 用 snapshot 更新今天的即時資料

    Args:
        api: Shioaji API 實例
        index_type: 'TSE' 或 'OTC'
        start: 開始日期
        force_refresh: 強制重新下載所有資料

    Returns:
        DataFrame: 包含完整資料 (包括今天)
    """
    today = pd.Timestamp.now().normalize()
    yesterday = today - pd.Timedelta(days=1)

    # 1. 嘗試載入快取
    cached_df = None if force_refresh else _load_from_cache(index_type)

    # 2. 檢查是否需要更新歷史資料
    if cached_df is None or _need_update_historical(cached_df):
        # 需要下載歷史資料
        if cached_df is None:
            # 完全沒有快取,下載全部
            print(
                f"📥 下載 {index_type} 完整歷史資料 ({start} ~ {yesterday.date()})..."
            )
            historical_df = get_index_with_macd(
                api,
                index_type=index_type,
                start=start,
                end=yesterday.strftime("%Y-%m-%d"),
            )
        else:
            # 有快取,只下載缺少的部分
            last_cached_date = cached_df.index.max()
            next_day = (last_cached_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

            print(f"📥 下載 {index_type} 增量資料 ({next_day} ~ {yesterday.date()})...")

            try:
                new_data = get_index_with_macd(
                    api,
                    index_type=index_type,
                    start=next_day,
                    end=yesterday.strftime("%Y-%m-%d"),
                )

                # 合併舊資料和新資料
                historical_df = pd.concat([cached_df, new_data])
                historical_df = historical_df[
                    ~historical_df.index.duplicated(keep="last")
                ]
                historical_df = historical_df.sort_index()

                # 重新計算均線 (因為新增資料後均線會改變)
                historical_df["ma5"] = (
                    historical_df["Close"].rolling(window=5).mean().round(2)
                )
                historical_df["ma20"] = (
                    historical_df["Close"].rolling(window=20).mean().round(2)
                )
                historical_df["ma60"] = (
                    historical_df["Close"].rolling(window=60).mean().round(2)
                )
                historical_df["ma120"] = (
                    historical_df["Close"].rolling(window=120).mean().round(2)
                )

                print(f"✅ 合併完成: 共 {len(historical_df)} 筆資料")

            except Exception as e:
                print(f"⚠️ 增量更新失敗,使用快取資料: {e}")
                historical_df = cached_df

        # 儲存到快取
        _save_to_cache(historical_df, index_type)
    else:
        # 快取資料已是最新
        historical_df = cached_df

    # 3. 更新今天的即時資料
    print(f"📡 取得 {index_type} 今日即時資料...")

    try:
        contract = (
            api.Contracts.Indexs.TSE.TSE001
            if index_type == "TSE"
            else api.Contracts.Indexs.OTC.OTC101
        )
        snapshot = api.snapshots([contract])[0]

        # 檢查今天是否已有資料
        if today in historical_df.index:
            # 更新今天的資料
            historical_df.loc[today, "Open"] = snapshot.open
            historical_df.loc[today, "High"] = max(
                historical_df.loc[today, "High"], snapshot.high
            )
            historical_df.loc[today, "Low"] = min(
                historical_df.loc[today, "Low"], snapshot.low
            )
            historical_df.loc[today, "Close"] = snapshot.close
            historical_df.loc[today, "Volume"] = snapshot.total_amount / 1e8
        else:
            # 新增今天的資料
            today_data = pd.Series(
                {
                    "Open": snapshot.open,
                    "High": snapshot.high,
                    "Low": snapshot.low,
                    "Close": snapshot.close,
                    "Volume": snapshot.total_amount / 1e8,
                    "DIF": np.nan,
                    "MACD": np.nan,
                    "MACD_Hist": np.nan,
                    "ma5": np.nan,
                    "ma20": np.nan,
                    "ma60": np.nan,
                    "ma120": np.nan,
                },
                name=today,
            )

            historical_df = pd.concat([historical_df, today_data.to_frame().T])

        # 重新計算今天的 MACD 和均線
        window_size = 50
        recent_data = historical_df.tail(window_size)

        macd_dif, macd_signal, macd_hist = talib.MACD(
            recent_data["Close"].values, fastperiod=12, slowperiod=26, signalperiod=9
        )

        if not np.isnan(macd_dif[-1]):
            historical_df.loc[today, "DIF"] = macd_dif[-1]
            historical_df.loc[today, "MACD"] = macd_signal[-1]
            historical_df.loc[today, "MACD_Hist"] = macd_hist[-1]

        # 計算均線
        if len(historical_df) >= 5:
            historical_df.loc[today, "ma5"] = historical_df["Close"].tail(5).mean()
        if len(historical_df) >= 20:
            historical_df.loc[today, "ma20"] = historical_df["Close"].tail(20).mean()
        if len(historical_df) >= 60:
            historical_df.loc[today, "ma60"] = historical_df["Close"].tail(60).mean()
        if len(historical_df) >= 120:
            historical_df.loc[today, "ma120"] = historical_df["Close"].tail(120).mean()

        print(f"✅ {index_type} 即時資料更新完成 (收盤: {snapshot.close:.2f})")

    except Exception as e:
        print(f"⚠️ 即時資料更新失敗: {e}")

    return historical_df


# 全域變數用於快取資料
_tse_cache = None
_otc_cache = None
_last_update = None


def get_cached_or_fetch(api, force_refresh=False, realtime_update=True):
    """
    取得快取的資料或重新抓取 (改進版,使用檔案快取)

    Args:
        api: Shioaji API 實例
        force_refresh: 是否強制重新抓取歷史資料
        realtime_update: 是否每次都更新即時資料 (預設 True)

    Returns:
        tuple: (tse_df, otc_df)
    """
    global _tse_cache, _otc_cache, _last_update

    now = datetime.now()

    # 檢查歷史資料快取是否需要更新 (每 1 小時檢查一次)
    need_historical_update = (
        _tse_cache is None
        or _otc_cache is None
        or force_refresh
        or _last_update is None
        or (now - _last_update).seconds > 3600  # 1 小時
    )

    if need_historical_update:
        print("=" * 60)
        print("🔄 更新歷史資料...")
        print("=" * 60)

        # 使用智慧快取機制 (載入歷史資料)
        _tse_cache = get_index_data_smart(api, "TSE", force_refresh=force_refresh)
        _otc_cache = get_index_data_smart(api, "OTC", force_refresh=force_refresh)
        _last_update = now

        print("=" * 60)
        print(f"✅ 歷史資料更新完成! 最後更新時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    # 如果啟用即時更新,每次都更新今天的資料
    if realtime_update:
        print(f"📡 更新即時資料... ({now.strftime('%H:%M:%S')})")

        try:
            # 取得即時 snapshot
            tse_contract = api.Contracts.Indexs.TSE.TSE001
            otc_contract = api.Contracts.Indexs.OTC.OTC101
            snapshots = api.snapshots([tse_contract, otc_contract])

            today = pd.Timestamp.now().normalize()

            # 更新 TSE
            tse_snapshot = snapshots[0]
            if today in _tse_cache.index:
                _tse_cache.loc[today, "Open"] = tse_snapshot.open
                _tse_cache.loc[today, "High"] = max(
                    _tse_cache.loc[today, "High"], tse_snapshot.high
                )
                _tse_cache.loc[today, "Low"] = min(
                    _tse_cache.loc[today, "Low"], tse_snapshot.low
                )
                _tse_cache.loc[today, "Close"] = tse_snapshot.close
                _tse_cache.loc[today, "Volume"] = tse_snapshot.total_amount / 1e8
            else:
                # 新增今天的資料
                _tse_cache.loc[today] = {
                    "Open": tse_snapshot.open,
                    "High": tse_snapshot.high,
                    "Low": tse_snapshot.low,
                    "Close": tse_snapshot.close,
                    "Volume": tse_snapshot.total_amount / 1e8,
                    "DIF": np.nan,
                    "MACD": np.nan,
                    "MACD_Hist": np.nan,
                    "ma5": np.nan,
                    "ma20": np.nan,
                    "ma60": np.nan,
                    "ma120": np.nan,
                }

            # 重新計算 TSE 今天的指標
            _recalculate_indicators(_tse_cache, today)

            # 更新 OTC
            otc_snapshot = snapshots[1]
            if today in _otc_cache.index:
                _otc_cache.loc[today, "Open"] = otc_snapshot.open
                _otc_cache.loc[today, "High"] = max(
                    _otc_cache.loc[today, "High"], otc_snapshot.high
                )
                _otc_cache.loc[today, "Low"] = min(
                    _otc_cache.loc[today, "Low"], otc_snapshot.low
                )
                _otc_cache.loc[today, "Close"] = otc_snapshot.close
                _otc_cache.loc[today, "Volume"] = otc_snapshot.total_amount / 1e8
            else:
                # 新增今天的資料
                _otc_cache.loc[today] = {
                    "Open": otc_snapshot.open,
                    "High": otc_snapshot.high,
                    "Low": otc_snapshot.low,
                    "Close": otc_snapshot.close,
                    "Volume": otc_snapshot.total_amount / 1e8,
                    "DIF": np.nan,
                    "MACD": np.nan,
                    "MACD_Hist": np.nan,
                    "ma5": np.nan,
                    "ma20": np.nan,
                    "ma60": np.nan,
                    "ma120": np.nan,
                }

            # 重新計算 OTC 今天的指標
            _recalculate_indicators(_otc_cache, today)

            print(
                f"✅ 即時資料更新完成 - TSE: {tse_snapshot.close:.2f}, OTC: {otc_snapshot.close:.2f}"
            )

        except Exception as e:
            print(f"⚠️ 即時資料更新失敗: {e}")
    else:
        print(
            f"ℹ️ 使用快取資料 (上次更新: {_last_update.strftime('%H:%M:%S') if _last_update else 'N/A'})"
        )

    return _tse_cache.copy(), _otc_cache.copy()


def _recalculate_indicators(df, today):
    """重新計算今天的技術指標 (MACD 和均線)"""
    import talib

    # 計算 MACD (使用最近 50 筆)
    window_size = min(50, len(df))
    recent_data = df.tail(window_size)

    macd_dif, macd_signal, macd_hist = talib.MACD(
        recent_data["Close"].values, fastperiod=12, slowperiod=26, signalperiod=9
    )

    if not np.isnan(macd_dif[-1]):
        df.loc[today, "DIF"] = macd_dif[-1]
        df.loc[today, "MACD"] = macd_signal[-1]
        df.loc[today, "MACD_Hist"] = macd_hist[-1]

    # 計算均線
    if len(df) >= 5:
        df.loc[today, "ma5"] = df["Close"].tail(5).mean()
    if len(df) >= 20:
        df.loc[today, "ma20"] = df["Close"].tail(20).mean()
    if len(df) >= 60:
        df.loc[today, "ma60"] = df["Close"].tail(60).mean()
    if len(df) >= 120:
        df.loc[today, "ma120"] = df["Close"].tail(120).mean()


def clear_cache():
    """清除所有快取 (包括檔案和記憶體)"""
    global _tse_cache, _otc_cache, _last_update

    # 清除記憶體快取
    _tse_cache = None
    _otc_cache = None
    _last_update = None

    # 清除檔案快取
    for cache_file in CACHE_DIR.glob("*.pkl"):
        try:
            cache_file.unlink()
            print(f"🗑️ 已刪除快取檔案: {cache_file.name}")
        except Exception as e:
            print(f"⚠️ 刪除快取失敗 {cache_file.name}: {e}")

    print("✅ 快取已清除")


# 全域變數用於快取資料 (舊版相容)
_tse_cache = None
_otc_cache = None
_last_update = None


def get_cached_or_fetch_old(api, force_refresh=False):
    """
    取得快取的資料或重新抓取 (舊版,僅記憶體快取)

    保留此函數以維持向後相容性
    建議使用新的 get_cached_or_fetch() 函數

    Args:
        api: Shioaji API 實例
        force_refresh: 是否強制重新抓取

    Returns:
        tuple: (tse_df, otc_df)
    """
    global _tse_cache, _otc_cache, _last_update

    now = datetime.now()

    # 如果沒有快取或超過 1 小時，或強制更新
    if (
        _tse_cache is None
        or _otc_cache is None
        or force_refresh
        or (_last_update and (now - _last_update).seconds > 3600)
    ):

        print("🔄 重新抓取歷史資料...")
        _tse_cache = get_index_with_macd(api, "TSE", "2024-01-01", "2025-12-01")
        _otc_cache = get_index_with_macd(api, "OTC", "2024-01-01", "2025-12-01")
        _last_update = now
        print("✅ 歷史資料載入完成")

    # 更新即時資料
    print("📡 更新即時資料...")
    tse_updated, otc_updated = update_both_indexes_realtime(_tse_cache, _otc_cache, api)

    return tse_updated, otc_updated
