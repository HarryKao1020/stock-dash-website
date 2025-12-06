"""測試應用程式記憶體使用量"""

import psutil
import os


def mb(bytes):
    return bytes / 1024 / 1024


process = psutil.Process(os.getpid())

print("=" * 50)
print("📊 記憶體使用量測試")
print("=" * 50)

# 階段 1: 基礎
print(f"\n🔹 基礎 Python: {mb(process.memory_info().rss):.1f} MB")

# 階段 2: 載入 pandas, numpy
import pandas as pd
import numpy as np

print(f"🔹 + pandas/numpy: {mb(process.memory_info().rss):.1f} MB")

# 階段 3: 載入 dash
from dash import Dash
import dash_bootstrap_components as dbc

print(f"🔹 + dash: {mb(process.memory_info().rss):.1f} MB")

# 階段 4: 載入 finlab_data
from finlab_data import finlab_data

print(f"🔹 + finlab_data: {mb(process.memory_info().rss):.1f} MB")

# 階段 5: 載入資料
_ = finlab_data.close
print(f"🔹 + 收盤價資料: {mb(process.memory_info().rss):.1f} MB")

_ = finlab_data.world_index_close
print(f"🔹 + 國際指數: {mb(process.memory_info().rss):.1f} MB")

print("\n" + "=" * 50)
print(f"✅ 總計: {mb(process.memory_info().rss):.1f} MB")
print(f"⚠️  Render Free: 512 MB")
print(f"✅ Render Starter: 2048 MB")
print("=" * 50)
