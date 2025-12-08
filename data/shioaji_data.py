"""
Shioaji API 資料處理模組 - 優化版
改進：
1. 更聰明的快取邏輯（避免重複計算）
2. 即時資料有獨立的更新間隔（預設 60 秒）
3. 只在資料真正變化時才重新計算指標
"""

import pandas as pd
import numpy as np
import talib
from datetime import datetime, date
from pathlib import Path
import pickle
from finlab import data
import sys
import time
import threading

# 匯入共用函數
sys.path.insert(0, str(Path(__file__).parent.parent))
from finlab_data import get_cache_dir

# 快取目錄
CACHE_DIR = get_cache_dir("shioaji")

# ============================================
# 🆕 全域快取變數
# ============================================
_tse_cache = None
_otc_cache = None
_last_historical_update = None  # 歷史資料上次更新時間
_last_realtime_update = None  # 即時資料上次更新時間
_cache_lock = threading.Lock()

# 🆕 快取設定
HISTORICAL_UPDATE_INTERVAL = 3600  # 歷史資料更新間隔（秒）= 1 小時
REALTIME_UPDATE_INTERVAL = 60  # 即時資料更新間隔（秒）= 1 分鐘


def get_transaction_amount_from_finlab():
    """從 FinLab 取得歷史成交金額資料"""
    try:
        print("📥 從 FinLab 取得成交金額資料...")
        money = data.get("market_transaction_info:成交金額")
        result = pd.DataFrame(
            {"TSE_Amount": money["TAIEX"] / 1e8, "OTC_Amount": money["OTC"] / 1e8}
        )
        result = result[result.index.dayofweek < 5]
        result = result.dropna()
        print(f"✅ FinLab 成交金額資料載入完成 (截至 {result.index.max().date()})")
        return result
    except Exception as e:
        print(f"⚠️ 無法從 FinLab 取得成交金額: {e}")
        return None


def _recalculate_all_indicators(df):
    """重新計算整個 DataFrame 的所有技術指標"""
    df = df.copy()
    df["DIF"], df["MACD"], df["MACD_Hist"] = talib.MACD(
        df["Close"].values, fastperiod=12, slowperiod=26, signalperiod=9
    )
    df["ma5"] = df["Close"].rolling(window=5).mean().round(2)
    df["ma20"] = df["Close"].rolling(window=20).mean().round(2)
    df["ma60"] = df["Close"].rolling(window=60).mean().round(2)
    df["ma120"] = df["Close"].rolling(window=120).mean().round(2)
    return df


def _recalculate_today_only(df, today):
    """
    🆕 只重新計算今天的指標（比重算整個 DataFrame 快很多）
    """
    # MACD - 只用最近 50 筆計算
    window_size = min(50, len(df))
    recent_close = df["Close"].tail(window_size).values

    macd_dif, macd_signal, macd_hist = talib.MACD(
        recent_close, fastperiod=12, slowperiod=26, signalperiod=9
    )

    if len(macd_dif) > 0 and not np.isnan(macd_dif[-1]):
        df.loc[today, "DIF"] = macd_dif[-1]
        df.loc[today, "MACD"] = macd_signal[-1]
        df.loc[today, "MACD_Hist"] = macd_hist[-1]

    # 均線 - 只計算今天的值
    if len(df) >= 5:
        df.loc[today, "ma5"] = df["Close"].tail(5).mean().round(2)
    if len(df) >= 20:
        df.loc[today, "ma20"] = df["Close"].tail(20).mean().round(2)
    if len(df) >= 60:
        df.loc[today, "ma60"] = df["Close"].tail(60).mean().round(2)
    if len(df) >= 120:
        df.loc[today, "ma120"] = df["Close"].tail(120).mean().round(2)

    return df


def get_index_with_macd(api, index_type="TSE", start="2024-10-01", end="2025-12-01"):
    """取得指數日線 + MACD + 均線"""
    contract = (
        api.Contracts.Indexs.TSE.TSE001
        if index_type == "TSE"
        else api.Contracts.Indexs.OTC.OTC101
    )

    kbars = api.kbars(contract=contract, start=start, end=end)
    df = pd.DataFrame(kbars.model_dump())
    df["ts"] = pd.to_datetime(df["ts"])
    df["date"] = df["ts"].dt.date

    daily = df.groupby("date").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Amount": "sum"}
    )

    daily.index = pd.to_datetime(daily.index)
    daily["Amount"] = daily["Amount"] / 1e8

    # 計算技術指標
    daily = _recalculate_all_indicators(daily)

    # 過濾週末
    daily = daily[daily.index.dayofweek < 5]
    daily = daily.dropna(subset=["Open", "High", "Low", "Close"])

    return daily[
        [
            "Open",
            "High",
            "Low",
            "Close",
            "Amount",
            "DIF",
            "MACD",
            "MACD_Hist",
            "ma5",
            "ma20",
            "ma60",
            "ma120",
        ]
    ]


def _get_cache_path(index_type):
    return CACHE_DIR / f"{index_type}_historical.pkl"


def _save_to_cache(df, index_type):
    try:
        cache_path = _get_cache_path(index_type)
        today = pd.Timestamp.now().normalize()
        historical_df = df[df.index < today].copy()
        with open(cache_path, "wb") as f:
            pickle.dump(historical_df, f)
        print(f"✅ {index_type} 歷史資料已儲存到快取")
        return True
    except Exception as e:
        print(f"⚠️ 儲存快取失敗: {e}")
        return False


def _load_from_cache(index_type):
    try:
        cache_path = _get_cache_path(index_type)
        if not cache_path.exists():
            return None
        with open(cache_path, "rb") as f:
            df = pickle.load(f)
        print(f"✅ 從快取載入 {index_type} 歷史資料 (截至 {df.index.max().date()})")
        return df
    except Exception as e:
        print(f"⚠️ 載入快取失敗: {e}")
        return None


def _need_update_historical(cached_df):
    if cached_df is None:
        return True
    last_date = cached_df.index.max()
    yesterday = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)
    return last_date < yesterday


def get_index_data_smart(
    api, index_type="TSE", start="2024-01-01", force_refresh=False
):
    """智慧取得指數資料（使用快取優化）"""
    today = pd.Timestamp.now().normalize()
    yesterday = today - pd.Timedelta(days=1)

    cached_df = None if force_refresh else _load_from_cache(index_type)
    finlab_amount = get_transaction_amount_from_finlab()

    if cached_df is None or _need_update_historical(cached_df):
        if cached_df is None:
            print(f"📥 下載 {index_type} 完整歷史資料...")
            historical_df = get_index_with_macd(
                api,
                index_type=index_type,
                start=start,
                end=yesterday.strftime("%Y-%m-%d"),
            )
        else:
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
                historical_df = pd.concat([cached_df, new_data])
                historical_df = historical_df[
                    ~historical_df.index.duplicated(keep="last")
                ]
                historical_df = historical_df.sort_index()
                historical_df = historical_df[historical_df.index.dayofweek < 5]
                historical_df = historical_df.dropna(
                    subset=["Open", "High", "Low", "Close"]
                )
                historical_df = _recalculate_all_indicators(historical_df)
            except Exception as e:
                print(f"⚠️ 增量更新失敗: {e}")
                historical_df = cached_df

        # 用 FinLab 成交金額
        if finlab_amount is not None:
            amount_col = "TSE_Amount" if index_type == "TSE" else "OTC_Amount"
            common_dates = historical_df.index.intersection(finlab_amount.index)
            historical_df.loc[common_dates, "Amount"] = finlab_amount.loc[
                common_dates, amount_col
            ]

        _save_to_cache(historical_df, index_type)
    else:
        historical_df = cached_df
        if finlab_amount is not None:
            amount_col = "TSE_Amount" if index_type == "TSE" else "OTC_Amount"
            common_dates = historical_df.index.intersection(finlab_amount.index)
            historical_df.loc[common_dates, "Amount"] = finlab_amount.loc[
                common_dates, amount_col
            ]

    # 取得今日即時資料
    try:
        contract = (
            api.Contracts.Indexs.TSE.TSE001
            if index_type == "TSE"
            else api.Contracts.Indexs.OTC.OTC101
        )
        snapshot = api.snapshots([contract])[0]

        if today in historical_df.index:
            historical_df.loc[today, "Open"] = snapshot.open
            historical_df.loc[today, "High"] = max(
                historical_df.loc[today, "High"], snapshot.high
            )
            historical_df.loc[today, "Low"] = min(
                historical_df.loc[today, "Low"], snapshot.low
            )
            historical_df.loc[today, "Close"] = snapshot.close
            historical_df.loc[today, "Amount"] = snapshot.total_amount / 1e8
        else:
            today_data = pd.Series(
                {
                    "Open": snapshot.open,
                    "High": snapshot.high,
                    "Low": snapshot.low,
                    "Close": snapshot.close,
                    "Amount": snapshot.total_amount / 1e8,
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

        # 只重算今天的指標
        historical_df = _recalculate_today_only(historical_df, today)

    except Exception as e:
        print(f"⚠️ 即時資料更新失敗: {e}")

    historical_df = historical_df[historical_df.index.dayofweek < 5]
    return historical_df


def get_cached_or_fetch(api, force_refresh=False):
    """
    🆕 優化版：更聰明的快取邏輯

    - 歷史資料：每小時檢查一次
    - 即時資料：每 60 秒更新一次（非交易時間不更新）
    - 頁面切換時：直接返回快取，不重新計算
    """
    global _tse_cache, _otc_cache, _last_historical_update, _last_realtime_update

    now = datetime.now()
    current_time = now.time()

    # 交易時間判斷
    trading_start = datetime.strptime("08:45", "%H:%M").time()
    trading_end = datetime.strptime("14:00", "%H:%M").time()
    is_trading_hours = trading_start <= current_time <= trading_end

    with _cache_lock:
        # ============================================
        # 1️⃣ 檢查是否需要更新歷史資料（每小時一次）
        # ============================================
        need_historical = (
            _tse_cache is None
            or _otc_cache is None
            or force_refresh
            or _last_historical_update is None
            or (now - _last_historical_update).seconds > HISTORICAL_UPDATE_INTERVAL
        )

        if need_historical:
            print("=" * 50)
            print("🔄 更新歷史資料...")
            start_time = time.time()

            _tse_cache = get_index_data_smart(api, "TSE", force_refresh=force_refresh)
            _otc_cache = get_index_data_smart(api, "OTC", force_refresh=force_refresh)
            _last_historical_update = now
            _last_realtime_update = now  # 歷史更新時也會更新即時

            elapsed = time.time() - start_time
            print(f"✅ 歷史資料更新完成! 耗時: {elapsed:.1f} 秒")
            print("=" * 50)

            return _tse_cache.copy(), _otc_cache.copy()

        # ============================================
        # 2️⃣ 檢查是否需要更新即時資料（每分鐘一次）
        # ============================================
        need_realtime = (
            is_trading_hours
            and _last_realtime_update is not None
            and (now - _last_realtime_update).seconds > REALTIME_UPDATE_INTERVAL
        )

        if need_realtime:
            print(f"📡 更新即時資料... ({now.strftime('%H:%M:%S')})")

            try:
                tse_contract = api.Contracts.Indexs.TSE.TSE001
                otc_contract = api.Contracts.Indexs.OTC.OTC101
                snapshots = api.snapshots([tse_contract, otc_contract])

                today = pd.Timestamp.now().normalize()

                # 更新 TSE
                tse_snap = snapshots[0]
                if today in _tse_cache.index:
                    _tse_cache.loc[today, "High"] = max(
                        _tse_cache.loc[today, "High"], tse_snap.high
                    )
                    _tse_cache.loc[today, "Low"] = min(
                        _tse_cache.loc[today, "Low"], tse_snap.low
                    )
                    _tse_cache.loc[today, "Close"] = tse_snap.close
                    _tse_cache.loc[today, "Amount"] = tse_snap.total_amount / 1e8
                _tse_cache = _recalculate_today_only(_tse_cache, today)

                # 更新 OTC
                otc_snap = snapshots[1]
                if today in _otc_cache.index:
                    _otc_cache.loc[today, "High"] = max(
                        _otc_cache.loc[today, "High"], otc_snap.high
                    )
                    _otc_cache.loc[today, "Low"] = min(
                        _otc_cache.loc[today, "Low"], otc_snap.low
                    )
                    _otc_cache.loc[today, "Close"] = otc_snap.close
                    _otc_cache.loc[today, "Amount"] = otc_snap.total_amount / 1e8
                _otc_cache = _recalculate_today_only(_otc_cache, today)

                _last_realtime_update = now
                print(
                    f"✅ 即時更新完成 - TSE: {tse_snap.close:.2f}, OTC: {otc_snap.close:.2f}"
                )

            except Exception as e:
                print(f"⚠️ 即時更新失敗: {e}")

        # ============================================
        # 3️⃣ 直接返回快取（最常見的情況）
        # ============================================
        else:
            if not is_trading_hours:
                pass  # 非交易時間，安靜地返回快取
            else:
                remaining = (
                    REALTIME_UPDATE_INTERVAL - (now - _last_realtime_update).seconds
                )
                # 不印 log，避免刷屏

        return _tse_cache.copy(), _otc_cache.copy()


def clear_cache():
    """清除所有快取"""
    global _tse_cache, _otc_cache, _last_historical_update, _last_realtime_update

    with _cache_lock:
        _tse_cache = None
        _otc_cache = None
        _last_historical_update = None
        _last_realtime_update = None

    for cache_file in CACHE_DIR.glob("*.pkl"):
        try:
            cache_file.unlink()
            print(f"🗑️ 已刪除: {cache_file.name}")
        except Exception as e:
            print(f"⚠️ 刪除失敗: {e}")

    print("✅ 快取已清除")
