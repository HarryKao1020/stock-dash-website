import pandas as pd
from datetime import datetime, timedelta
import os
import dotenv
from pathlib import Path
import threading
import atexit
import finlab
from finlab import data

# 載入環境變數
dotenv.load_dotenv()

# 這裡要替換成自己的FinLab VIP token
token = os.getenv("FINLAB_TOKEN")
finlab.login(token)

# 取得專案目錄
PROJECT_DIR = Path(__file__).parent

# 快取目錄（本地和 VPS 都用專案目錄下的 cache）
CACHE_DIR = PROJECT_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 定時更新設定（預設 2 小時 = 7200 秒）
AUTO_REFRESH_INTERVAL = 2 * 60 * 60  # 秒


def get_cache_dir(subdir: str = "") -> Path:
    """
    取得快取目錄

    Args:
        subdir: 子目錄名稱，例如 "shioaji"

    Returns:
        Path: 快取目錄路徑
    """
    cache_dir = CACHE_DIR / subdir if subdir else CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_price_data(field="price:收盤價", cache_hours=24):
    """
    取得價格資料,支援快取

    Args:
        field: FinLab 資料欄位
        cache_hours: 快取有效時間(小時)

    Returns:
        pd.DataFrame: 價格資料
    """
    cache_file = CACHE_DIR / f'{field.replace(":", "_").replace("/", "_")}.pkl'
    cache_time_file = CACHE_DIR / f'{field.replace(":", "_").replace("/", "_")}.time'

    # 檢查快取是否存在且未過期
    if cache_file.exists() and cache_time_file.exists():
        with open(cache_time_file, "r") as f:
            cache_time = datetime.fromisoformat(f.read())

        if datetime.now() - cache_time < timedelta(hours=cache_hours):
            print(f"✓ 讀取快取: {field}")
            return pd.read_pickle(cache_file)

    # 下載新資料
    print(f"↓ 下載資料: {field}")
    df = data.get(field)

    # 儲存快取
    df.to_pickle(cache_file)
    with open(cache_time_file, "w") as f:
        f.write(datetime.now().isoformat())

    return df


class FinLabData:
    """FinLab 資料管理類別"""

    def __init__(
        self, auto_refresh: bool = False, refresh_interval: int = AUTO_REFRESH_INTERVAL
    ):
        """
        初始化 FinLabData

        Args:
            auto_refresh: 是否啟用自動定時更新
            refresh_interval: 更新間隔（秒），預設 2 小時
        """
        self._close = None
        self._open = None
        self._high = None
        self._low = None
        self._volume = None
        self._amount = None  # 成交金額
        # self._change_pct = None # 漲跌幅
        self._company_names = None  # 快取公司名稱

        # 融資相關資料
        self._margin_balance = None  # 融資今日餘額
        self._margin_total = None  # 融資券總餘額
        self._benchmark = None  # 大盤指數
        self._margin_maintenance_ratio = None  # 融資維持率

        # 國際指數相關資料
        self._world_index_open = None
        self._world_index_close = None
        self._world_index_high = None
        self._world_index_low = None
        self._world_index_vol = None

        # 處置股和警示股資料
        self._disposal_stock = None
        self._noticed_stock = None

        # 🆕 月營收相關資料
        self._monthly_revenue = None  # 當月營收
        self._revenue_yoy = None  # 去年同月增減(%)
        self._revenue_mom = None  # 上月比較增減(%)

        # 定時更新相關
        self._auto_refresh = auto_refresh
        self._refresh_interval = refresh_interval
        self._refresh_timer = None
        self._is_running = False
        self._last_refresh_time = None

        # 如果啟用自動更新，則開始定時器
        if auto_refresh:
            self.start_auto_refresh()

    # ==================== 定時更新相關方法 ====================

    def start_auto_refresh(self):
        """啟動自動定時更新"""
        if self._is_running:
            print("⚠️ 自動更新已經在運行中")
            return

        self._is_running = True
        self._schedule_next_refresh()
        print(f"✅ 已啟動自動更新，每 {self._refresh_interval / 3600:.1f} 小時更新一次")

        # 註冊程式結束時的清理函數
        atexit.register(self.stop_auto_refresh)

    def stop_auto_refresh(self):
        """停止自動定時更新"""
        self._is_running = False
        if self._refresh_timer is not None:
            self._refresh_timer.cancel()
            self._refresh_timer = None
        print("🛑 已停止自動更新")

    def _schedule_next_refresh(self):
        """排程下一次更新"""
        if not self._is_running:
            return

        self._refresh_timer = threading.Timer(
            self._refresh_interval, self._auto_refresh_callback
        )
        self._refresh_timer.daemon = True  # 設為 daemon，主程式結束時自動終止
        self._refresh_timer.start()

        next_time = datetime.now() + timedelta(seconds=self._refresh_interval)
        print(f"⏰ 下次更新時間: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def _auto_refresh_callback(self):
        """自動更新的回呼函數"""
        if not self._is_running:
            return

        print(f"\n{'='*50}")
        print(f"🔄 開始自動更新資料 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        try:
            self.refresh()
            self._last_refresh_time = datetime.now()
            print(
                f"✅ 自動更新完成 - {self._last_refresh_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            print(f"❌ 自動更新失敗: {e}")

        # 排程下一次更新
        self._schedule_next_refresh()

    def set_refresh_interval(self, hours: float = 2):
        """
        設定更新間隔

        Args:
            hours: 更新間隔（小時）
        """
        self._refresh_interval = int(hours * 3600)
        print(f"📝 已設定更新間隔為 {hours} 小時")

        # 如果正在運行，重新排程
        if self._is_running:
            if self._refresh_timer is not None:
                self._refresh_timer.cancel()
            self._schedule_next_refresh()

    def get_refresh_status(self) -> dict:
        """
        取得自動更新狀態

        Returns:
            dict: 包含更新狀態的字典
        """
        return {
            "is_running": self._is_running,
            "refresh_interval_hours": self._refresh_interval / 3600,
            "last_refresh_time": (
                self._last_refresh_time.strftime("%Y-%m-%d %H:%M:%S")
                if self._last_refresh_time
                else None
            ),
            "next_refresh_time": (
                (
                    datetime.now() + timedelta(seconds=self._refresh_timer.interval)
                ).strftime("%Y-%m-%d %H:%M:%S")
                if self._refresh_timer and self._is_running
                else None
            ),
        }

    # ==================== 原有的 Property 方法 ====================

    @property
    def close(self):
        """收盤價"""
        if self._close is None:
            self._close = get_price_data("price:收盤價")
        return self._close

    @property
    def open(self):
        """開盤價"""
        if self._open is None:
            self._open = get_price_data("price:開盤價")
        return self._open

    @property
    def high(self):
        """最高價"""
        if self._high is None:
            self._high = get_price_data("price:最高價")
        return self._high

    @property
    def low(self):
        """最低價"""
        if self._low is None:
            self._low = get_price_data("price:最低價")
        return self._low

    @property
    def volume(self):
        """成交量"""
        if self._volume is None:
            self._volume = get_price_data("price:成交股數")
        return self._volume

    @property
    def change_pct(self):
        """漲跌幅"""
        if self._change_pct is None:
            self._change_pct = self.close - self.close.shift(1)
        return self._change_pct

    @property
    def amount(self):
        """成交金額"""
        if self._amount is None:
            self._amount = get_price_data("price:成交金額", cache_hours=12)
            # 確保數值為 float
            self._amount = self._amount.astype(float)
        return self._amount

    @property
    def margin_balance(self):
        """融資今日餘額"""
        if self._margin_balance is None:
            self._margin_balance = get_price_data(
                "margin_transactions:融資今日餘額", cache_hours=24
            )
        return self._margin_balance

    @property
    def margin_total(self):
        """融資券總餘額(含買賣超計算)"""
        if self._margin_total is None:
            融資券總餘額 = get_price_data("margin_balance:融資券總餘額", cache_hours=24)

            # 對齊索引
            融資券總餘額 = 融資券總餘額.loc[
                self.margin_balance.index.intersection(融資券總餘額.index)
            ]

            # 計算買賣超
            融資券總餘額["上市融資買賣超"] = (
                融資券總餘額["上市融資交易金額"]
                - 融資券總餘額["上市融資交易金額"].shift()
            ).fillna(0) / 100000000

            融資券總餘額["上櫃融資買賣超"] = (
                融資券總餘額["上櫃融資交易金額"]
                - 融資券總餘額["上櫃融資交易金額"].shift()
            ).fillna(0) / 100000000

            self._margin_total = 融資券總餘額

        return self._margin_total

    @property
    def benchmark(self):
        """大盤加權報酬指數"""
        if self._benchmark is None:
            self._benchmark = get_price_data(
                "benchmark_return:發行量加權股價報酬指數", cache_hours=24
            ).squeeze()
        return self._benchmark

    @property
    def margin_maintenance_ratio(self):
        """融資維持率"""
        if self._margin_maintenance_ratio is None:
            # 計算融資總餘額
            融資總餘額 = self.margin_total[
                ["上市融資交易金額", "上櫃融資交易金額"]
            ].sum(axis=1)

            # 計算融資餘額市值
            融資餘額市值 = (self.margin_balance * self.close * 1000).sum(axis=1)

            # 計算融資維持率
            self._margin_maintenance_ratio = 融資餘額市值 / 融資總餘額

        return self._margin_maintenance_ratio

    @property
    def world_index_open(self):
        """國際指數開盤價"""
        if self._world_index_open is None:
            self._world_index_open = get_price_data("world_index:open", cache_hours=12)
        return self._world_index_open

    @property
    def world_index_close(self):
        """國際指數收盤價"""
        if self._world_index_close is None:
            self._world_index_close = get_price_data(
                "world_index:close", cache_hours=12
            )
        return self._world_index_close

    @property
    def world_index_high(self):
        """國際指數最高價"""
        if self._world_index_high is None:
            self._world_index_high = get_price_data("world_index:high", cache_hours=12)
        return self._world_index_high

    @property
    def world_index_low(self):
        """國際指數最低價"""
        if self._world_index_low is None:
            self._world_index_low = get_price_data("world_index:low", cache_hours=12)
        return self._world_index_low

    @property
    def world_index_vol(self):
        """國際指數成交量"""
        if self._world_index_vol is None:
            self._world_index_vol = get_price_data("world_index:vol", cache_hours=12)
        return self._world_index_vol

    @property
    def disposal_stock(self):
        """非處置股過濾器"""
        if self._disposal_stock is None:
            self._disposal_stock = get_price_data(
                "etl:disposal_stock_filter", cache_hours=24
            )
        return self._disposal_stock

    @property
    def noticed_stock(self):
        """非注意股過濾器"""
        if self._noticed_stock is None:
            self._noticed_stock = get_price_data(
                "etl:noticed_stock_filter", cache_hours=24
            )
        return self._noticed_stock

    # ==================== 🆕 月營收相關屬性 ====================

    @property
    def monthly_revenue(self):
        """當月營收"""
        if self._monthly_revenue is None:
            self._monthly_revenue = (
                get_price_data("monthly_revenue:當月營收", cache_hours=24) * 1000
            )  # 轉換成千為初始單位
        return self._monthly_revenue

    @property
    def revenue_yoy(self):
        """營收年增率 (去年同月增減%)"""
        if self._revenue_yoy is None:
            self._revenue_yoy = get_price_data(
                "monthly_revenue:去年同月增減(%)", cache_hours=24
            )
        return self._revenue_yoy

    @property
    def revenue_mom(self):
        """營收月增率 (上月比較增減%)"""
        if self._revenue_mom is None:
            self._revenue_mom = get_price_data(
                "monthly_revenue:上月比較增減(%)", cache_hours=24
            )
        return self._revenue_mom

    # ==================== 🆕 月營收相關方法 ====================

    def get_ma_status(self, stock_id):
        """
        取得單一股票的均線排列狀態

        Args:
            stock_id: 股票代號

        Returns:
            str: 均線排列狀態
        """
        try:
            close = self.close[stock_id].dropna()
            if len(close) < 60:
                return "資料不足"

            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1]

            if ma5 > ma20 and ma20 > ma60:
                return "多頭排列"
            elif ma5 > ma20 and ma20 < ma60:
                return "谷底反彈"
            elif ma5 < ma20 and ma20 < ma60:
                return "空頭排列"
            elif ma5 < ma20 and ma20 > ma60:
                return "短期修正"
            else:
                return "盤整"

        except Exception as e:
            return "N/A"

    def get_revenue_ranking(self, sort_by="yoy", top_n=100):
        """
        取得月營收排行資料

        Args:
            sort_by: 排序依據 ('yoy' 或 'mom')
            top_n: 取前幾名

        Returns:
            DataFrame: 月營收排行資料
        """
        try:
            # 取得最新一期的營收資料
            rev = self.monthly_revenue
            rev_yoy = self.revenue_yoy
            rev_mom = self.revenue_mom
            amount = self.amount

            # 取得最新日期的資料
            latest_rev_date = rev.index[-1]
            latest_amount_date = amount.index[-1]

            print(f"📊 營收資料日期: {latest_rev_date}")
            print(f"📊 成交金額資料日期: {latest_amount_date}")

            # 取得當期營收資料
            rev_latest = rev.loc[latest_rev_date].dropna()
            yoy_latest = rev_yoy.loc[latest_rev_date].dropna()
            mom_latest = rev_mom.loc[latest_rev_date].dropna()
            amount_latest = amount.loc[latest_amount_date].dropna()

            # 找出共同的股票
            common_stocks = (
                rev_latest.index.intersection(yoy_latest.index)
                .intersection(mom_latest.index)
                .intersection(amount_latest.index)
            )

            print(f"📊 共同股票數量: {len(common_stocks)}")

            # 建立結果 DataFrame
            result_data = []

            for stock_id in common_stocks:
                try:
                    result_data.append(
                        {
                            "股票代號": stock_id,
                            "公司名稱": self.get_stock_name(stock_id),
                            "本月營收(億)": rev_latest[stock_id] / 1e8,
                            "營收YoY(%)": yoy_latest[stock_id],
                            "營收MoM(%)": mom_latest[stock_id],
                            "成交金額(億)": amount_latest[stock_id] / 1e8,
                            "均線排列": self.get_ma_status(stock_id),
                        }
                    )
                except Exception as e:
                    continue

            result = pd.DataFrame(result_data)

            if result.empty:
                return result, latest_rev_date

            # 排序
            if sort_by == "yoy":
                result = result.sort_values("營收YoY(%)", ascending=False)
            elif sort_by == "mom":
                result = result.sort_values("營收MoM(%)", ascending=False)
            elif sort_by == "revenue":
                result = result.sort_values("本月營收(億)", ascending=False)
            elif sort_by == "amount":
                result = result.sort_values("成交金額(億)", ascending=False)

            # 取前 N 名
            result = result.head(top_n).reset_index(drop=True)

            # 加入排名
            result.insert(0, "排名", range(1, len(result) + 1))

            return result, latest_rev_date

        except Exception as e:
            print(f"❌ 取得營收排行錯誤: {e}")
            import traceback

            traceback.print_exc()
            return pd.DataFrame(), None

    def get_disposal_stock_count(self, days=30):
        """
        取得處置股數量的時間序列資料

        Args:
            days: 取得最近幾天的資料

        Returns:
            pd.Series: 處置股數量時間序列
        """
        disposal_df = self.disposal_stock.tail(days * 2)  # 取兩倍天數確保有足夠的工作日
        # False 代表是處置股，計算每天有多少處置股
        count_series = (disposal_df == False).sum(axis=1)

        # 過濾週末（只保留週一到週五）
        weekday_mask = count_series.index.dayofweek < 5
        count_series = count_series[weekday_mask]

        # 取最後 days 天
        count_series = count_series.tail(days)

        return count_series

    def get_noticed_stock_count(self, days=30):
        """
        取得警示股數量的時間序列資料

        Args:
            days: 取得最近幾天的資料

        Returns:
            pd.Series: 警示股數量時間序列
        """
        noticed_df = self.noticed_stock.tail(days * 2)  # 取兩倍天數確保有足夠的工作日
        # False 代表是警示股，計算每天有多少警示股
        count_series = (noticed_df == False).sum(axis=1)

        # 過濾週末（只保留週一到週五）
        weekday_mask = count_series.index.dayofweek < 5
        count_series = count_series[weekday_mask]

        # 取最後 days 天
        count_series = count_series.tail(days)

        return count_series

    def get_current_disposal_stocks(self):
        """取得當前處置股列表"""
        latest = self.disposal_stock.iloc[-1]
        disposal_stocks = latest[latest == False].index.tolist()
        return disposal_stocks

    def get_current_noticed_stocks(self):
        """取得當前警示股列表"""
        latest = self.noticed_stock.iloc[-1]
        noticed_stocks = latest[latest == False].index.tolist()
        return noticed_stocks

    def get_top_amount_stocks(self, date_offset=0, top_n=100):
        """
        取得指定日期的成交金額前 N 名

        Args:
            date_offset: 日期偏移量 (0 = 最新一天, 1 = 前一天, ...)
            top_n: 取前幾名

        Returns:
            tuple: (DataFrame, target_date)
        """
        df = self.amount

        # 取得指定日期的資料
        date_idx = -(date_offset + 1)  # -1 是最後一筆, -2 是倒數第二筆...

        if abs(date_idx) > len(df):
            date_idx = -len(df)

        target_date = df.index[date_idx]
        day_data = df.loc[target_date].dropna()

        # 確保數值為 float 並排序
        day_data = day_data.astype(float)
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
        result["股票名稱"] = result["股票代號"].apply(self.get_stock_name)

        # 建立顯示標籤
        result["顯示標籤"] = result.apply(
            lambda row: (
                f"{row['股票代號']} {row['股票名稱']}"
                if row["股票名稱"]
                else row["股票代號"]
            ),
            axis=1,
        )

        return result, target_date

    def get_world_index_data(self, index_code, days=360):
        """
        取得國際指數的完整資料

        Args:
            index_code: 指數代碼 (如 "^TWII", "^GSPC", "^DJI" 等)
            days: 取得最近幾天的資料

        Returns:
            pd.DataFrame: 包含 OHLCV 的資料
        """
        df = pd.DataFrame(
            {
                "open": self.world_index_open[index_code],
                "high": self.world_index_high[index_code],
                "low": self.world_index_low[index_code],
                "close": self.world_index_close[index_code],
                "volume": self.world_index_vol[index_code],
            }
        ).dropna(subset=["close"])

        # 將 volume 的 NaN 填充為 0
        df["volume"] = df["volume"].fillna(0)

        # 🆕 過濾週末和假日（只保留有交易的日期）
        # 方法 1: 移除週末（週六=5, 週日=6）
        df = df[df.index.dayofweek < 5]

        # 方法 2: 更嚴格的過濾 - 移除所有 OHLC 都相同的日期（假日）
        df = df[
            ~(
                (df["open"] == df["high"])
                & (df["high"] == df["low"])
                & (df["low"] == df["close"])
                & (df["close"] == 0)
            )
        ]

        # 只取最近 N 天
        df = df.tail(days)

        # 計算移動平均線
        df["ma20"] = df["close"].rolling(window=20).mean()
        df["ma60"] = df["close"].rolling(window=60).mean()
        df["ma120"] = df["close"].rolling(window=120).mean()

        return df

    def get_stock_data(self, stock_id, start_date=None, end_date=None):
        """
        取得單一股票的完整資料

        Args:
            stock_id: 股票代號
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            pd.DataFrame: 包含 OHLCV 的資料
        """
        df = pd.DataFrame(
            {
                "open": self.open[stock_id],
                "high": self.high[stock_id],
                "low": self.low[stock_id],
                "close": self.close[stock_id],
                "volume": self.volume[stock_id],
            }
        )

        # 日期篩選
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        return df

    def get_margin_data(self):
        """
        取得融資相關完整資料

        Returns:
            tuple: (融資維持率, 融資券總餘額, 大盤指數, 收盤價)
        """
        return (
            self.margin_maintenance_ratio,
            self.margin_total,
            self.benchmark,
            self.close,
        )

    def get_stock_list(self):
        """取得所有股票代號列表(包含名稱)"""
        stock_ids = self.close.columns.tolist()

        # 如果已經快取過名稱,直接使用
        if self._company_names is None:
            try:
                print("📊 載入公司名稱資料...")
                company_info = data.get("company_basic_info")

                # 轉換成字典: {stock_id: 公司簡稱}
                self._company_names = {}
                for _, row in company_info.iterrows():
                    stock_id = str(row["stock_id"])
                    company_name = row["公司簡稱"]
                    self._company_names[stock_id] = company_name

                print(f"✓ 成功載入 {len(self._company_names)} 個公司名稱")

            except Exception as e:
                print(f"⚠️ 無法取得股票名稱: {e}")
                self._company_names = {}

        # 組合股票列表 "代號 名稱"
        stock_list = []
        for sid in stock_ids:
            name = self._company_names.get(sid, "")
            stock_list.append(f"{sid} {name}" if name else sid)

        return stock_list

    def get_stock_name(self, stock_id):
        """
        取得單一股票的名稱

        Args:
            stock_id: 股票代號

        Returns:
            str: 公司簡稱
        """
        # 確保已載入公司名稱
        if self._company_names is None:
            self.get_stock_list()

        return self._company_names.get(stock_id, "")

    def refresh(self):
        """強制重新下載所有資料"""
        print("🔄 清除快取並重新下載...")
        self._close = None
        self._open = None
        self._high = None
        self._low = None
        self._volume = None
        self._amount = None  # 成交金額
        self._company_names = None

        # 清除融資相關快取
        self._margin_balance = None
        self._margin_total = None
        self._benchmark = None
        self._margin_maintenance_ratio = None

        # 清除國際指數快取
        self._world_index_open = None
        self._world_index_close = None
        self._world_index_high = None
        self._world_index_low = None
        self._world_index_vol = None

        # 清除處置股和警示股快取
        self._disposal_stock = None
        self._noticed_stock = None

        # 🆕 清除月營收快取
        self._monthly_revenue = None
        self._revenue_yoy = None
        self._revenue_mom = None

        # 清除快取檔案（只刪除檔案，不刪除目錄本身，避免 Docker volume 問題）
        import shutil

        if CACHE_DIR.exists():
            for item in CACHE_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

        # 更新最後更新時間
        self._last_refresh_time = datetime.now()


# 建立全域實例（預設不啟用自動更新，可手動啟用）
finlab_data = FinLabData(auto_refresh=False)


# ==================== 便利函數 ====================


def get_close():
    """快速取得收盤價"""
    return finlab_data.close


def get_volume():
    """快速取得成交量"""
    return finlab_data.volume


def get_amount():
    """快速取得成交金額"""
    return finlab_data.amount


def get_stock_list():
    """快速取得股票列表(含名稱)"""
    return finlab_data.get_stock_list()


def get_stock_name(stock_id):
    """快速取得股票名稱"""
    return finlab_data.get_stock_name(stock_id)


def get_margin_data():
    """快速取得融資相關資料"""
    return finlab_data.get_margin_data()


def get_world_index_data(index_code, days=120):
    """快速取得國際指數資料"""
    return finlab_data.get_world_index_data(index_code, days)


def get_disposal_stock_count(days=30):
    """快速取得處置股數量"""
    return finlab_data.get_disposal_stock_count(days)


def get_noticed_stock_count(days=30):
    """快速取得警示股數量"""
    return finlab_data.get_noticed_stock_count(days)


def get_top_amount_stocks(date_offset=0, top_n=100):
    """快速取得成交金額前 N 名"""
    return finlab_data.get_top_amount_stocks(date_offset, top_n)


# 🆕 月營收相關便利函數
def get_revenue_ranking(sort_by="yoy", top_n=100):
    """快速取得月營收排行"""
    return finlab_data.get_revenue_ranking(sort_by, top_n)


# ==================== 🆕 自動更新相關便利函數 ====================


def start_auto_refresh(interval_hours: float = 2):
    """
    啟動自動定時更新

    Args:
        interval_hours: 更新間隔（小時），預設 2 小時
    """
    finlab_data.set_refresh_interval(interval_hours)
    finlab_data.start_auto_refresh()


def stop_auto_refresh():
    """停止自動定時更新"""
    finlab_data.stop_auto_refresh()


def get_refresh_status():
    """取得自動更新狀態"""
    return finlab_data.get_refresh_status()
