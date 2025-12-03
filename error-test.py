"""
診斷 K線圖空白問題
"""

import pandas as pd
import numpy as np

print("=" * 60)
print("🔍 診斷 K線圖空白問題")
print("=" * 60)

# 模擬測試資料
dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")
test_df = pd.DataFrame(
    {
        "Open": np.random.randn(30).cumsum() + 20000,
        "High": np.random.randn(30).cumsum() + 20100,
        "Low": np.random.randn(30).cumsum() + 19900,
        "Close": np.random.randn(30).cumsum() + 20000,
        "Amount": np.random.rand(30) * 3000 + 2000,
    },
    index=dates,
)

print("\n1️⃣ 檢查資料結構:")
print("-" * 60)
print(f"資料筆數: {len(test_df)}")
print(f"日期範圍: {test_df.index.min()} ~ {test_df.index.max()}")
print(f"\n資料前5筆:")
print(test_df.head())

print("\n2️⃣ 檢查是否有 NaN:")
print("-" * 60)
print(test_df.isna().sum())

print("\n3️⃣ 檢查週末日期:")
print("-" * 60)
weekend_dates = test_df[test_df.index.dayofweek >= 5]
print(f"週末筆數: {len(weekend_dates)}")
if len(weekend_dates) > 0:
    print("週末日期:")
    print(weekend_dates.index.tolist())

print("\n4️⃣ 可能的問題:")
print("-" * 60)
print(
    """
問題 1: 資料包含週末
  → 解決: 在載入資料時過濾週末
  
問題 2: rangebreaks 設定錯誤
  → 解決: 檢查 fig.update_xaxes 的設定
  
問題 3: 資料型態錯誤
  → 解決: 確保索引是 datetime 格式
  
問題 4: 所有子圖沒有同步
  → 解決: 確保 shared_xaxes=True
"""
)

print("\n5️⃣ 建議的修正方式:")
print("-" * 60)
print(
    """
方法 1: 在資料源頭過濾週末（推薦）⭐
---------------------------------------
# 在 shioaji_data.py 中
df = df[df.index.dayofweek < 5]  # 只保留週一到週五

方法 2: 使用更明確的 rangebreaks
---------------------------------------
# 在圖表中
fig.update_xaxes(
    rangebreaks=[
        dict(bounds=["sat", "mon"]),
    ],
    type="date"  # 明確指定類型
)

方法 3: 檢查資料完整性
---------------------------------------
# 移除 NaN 和無效資料
df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
df = df[df['Close'] > 0]
"""
)
