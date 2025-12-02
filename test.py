# # 在其他地方也可以這樣使用 finlab_data.py

# from finlab_data import finlab_data, get_close, get_stock
import finlab
from finlab import data
from finlab_data import finlab_data


# # 方法1: 使用全域實例
# close = finlab_data.close
# volume = finlab_data.volume

# # 方法2: 使用便利函數
# close = get_close()

# # 方法3: 取得單一股票
# tsmc = get_stock("2330", start_date="2024-11-09")
# print(tsmc.head())

# stock_list = finlab_data.get_stock_list()
# print(f"總共有 {len(stock_list)} 支股票")

from finlab_data import finlab_data

# 檢查資料結構
print("=" * 50)
print("檢查 FinLab 資料結構")
print("=" * 50)

close = finlab_data.close
print(f"\n資料形狀: {close.shape}")
print(f"欄位類型: {type(close.columns[0])}")
print(f"前10個欄位: {close.columns[:500].tolist()}")
print(f"日期範圍: {close.index[0]} ~ {close.index[-1]}")

# 測試取得單一股票
stock_id = close.columns[0]
stock_id = "2330"
print(f"\n測試取得股票: {stock_id}")
df = finlab_data.get_stock_data(stock_id)
print(df.head())
print(f"資料筆數: {len(df)}")


# 測試 get_stock_list
# print("=" * 50)
# print("測試 get_stock_list()")
# print("=" * 50)

# stock_list = finlab_data.get_stock_list()

# print(f"\n總共有 {len(stock_list)} 檔股票\n")
# print("前 20 個股票:")
# for i, stock in enumerate(stock_list[:20], 1):
#     print(f"{i:2d}. {stock}")

# print("\n最後 5 個股票:")
# for stock in stock_list[-5:]:
#     print(f"  - {stock}")

world_index_open = data.get("world_index:open")
world_index_close = data.get("world_index:close")
world_index_high = data.get("world_index:high")
world_index_low = data.get("world_index:low")
world_index_vol = data.get("world_index:vol")

# 韓國指數開收高低量
korea_index_open = world_index_open["^KS11"]

# 台灣指數開收高低量
tw_index_open = world_index_open["^TWII"]
print(tw_index_open)

# S&P 500
sp500_index_open = world_index_open["^GSPC"]

# Dow Jones
dj_index_open = world_index_open["^DJI"]

# NASDAQ
nasdaq_index_open = world_index_open["^IXIC"]

# 日經
japan_index_open = world_index_open["^N225"]

# print(japan_index_open)

# print(finlab_data.get_world_index_data("^TWII", 60))
# 測試程式 - 放在專案根目錄執行
from finlab_data import finlab_data

# 檢查國際指數資料
print("檢查國際指數資料...")
world_close = finlab_data.world_index_close

print(f"\n可用的指數代碼: {world_close.columns.tolist()}")
print(f"\n資料日期範圍: {world_close.index.min()} ~ {world_close.index.max()}")
print(f"最新資料日期: {world_close.index.max()}")

# 檢查台灣指數
if "^TWII" in world_close.columns:
    tw_data = world_close["^TWII"].dropna()
    print(f"\n台灣指數最新10筆:")
    print(tw_data.tail(10))
