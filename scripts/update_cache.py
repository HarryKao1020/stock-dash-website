#!/usr/bin/env python3
"""
定期更新 FinLab 快取資料（Parquet 格式）

用途：
- 由 cron job 定期執行（建議：交易日早上 7:30）
- 預先下載並快取資料，使用者存取時直接讀取快取
- 搭配 Parquet 格式，大幅減少快取檔案大小（~813 MB → ~80-160 MB）

執行方式：
  python scripts/update_cache.py

Docker 環境：
  docker-compose exec web python scripts/update_cache.py

Cron 設定範例（交易日早上 7:30）：
  30 7 * * 1-5 cd /path/to/project && docker-compose exec -T web python scripts/update_cache.py >> logs/cache_update.log 2>&1
"""

import sys
from pathlib import Path
from datetime import datetime

# 加入專案路徑
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from data.finlab_data import FinLabData

def main():
    """執行快取更新"""
    start_time = datetime.now()

    print("=" * 70)
    print(f"🔄 FinLab 快取更新開始")
    print(f"⏰ 開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        # 建立 FinLabData 實例（使用 Parquet 格式）
        finlab = FinLabData(use_parquet=True)

        # 強制刷新所有快取
        print("\n🗑️  清除舊快取...")
        finlab.refresh()

        print("\n📥 重新下載資料（Parquet 格式）...")

        # 主動觸發所有常用資料的載入（利用 lazy loading 機制）
        data_items = [
            # OHLCV 資料
            ("收盤價", lambda: finlab.close),
            ("開盤價", lambda: finlab.open),
            ("最高價", lambda: finlab.high),
            ("最低價", lambda: finlab.low),
            ("成交量", lambda: finlab.volume),
            ("成交金額", lambda: finlab.amount),

            # 融資資料
            ("融資餘額", lambda: finlab.margin_balance),
            ("融資總餘額", lambda: finlab.margin_total),
            ("大盤指數", lambda: finlab.benchmark),

            # 世界指數
            ("世界指數開盤", lambda: finlab.world_index_open),
            ("世界指數收盤", lambda: finlab.world_index_close),
            ("世界指數最高", lambda: finlab.world_index_high),
            ("世界指數最低", lambda: finlab.world_index_low),
            ("世界指數成交量", lambda: finlab.world_index_vol),

            # 股票篩選
            ("處置股過濾", lambda: finlab.disposal_stock),
            ("警示股過濾", lambda: finlab.noticed_stock),

            # 營收資料
            ("當月營收", lambda: finlab.monthly_revenue),
            ("營收YoY", lambda: finlab.revenue_yoy),
            ("營收MoM", lambda: finlab.revenue_mom),
        ]

        print(f"\n📊 預載 {len(data_items)} 項資料...")
        success_count = 0
        failed_items = []

        for name, getter in data_items:
            try:
                data = getter()
                if data is not None:
                    if hasattr(data, 'shape'):
                        print(f"   ✅ {name:<20} - 形狀: {data.shape}")
                    else:
                        print(f"   ✅ {name:<20} - 已載入")
                    success_count += 1
                else:
                    print(f"   ⚠️  {name:<20} - 資料為 None")
                    failed_items.append(name)
            except Exception as e:
                print(f"   ❌ {name:<20} - 錯誤: {str(e)[:50]}")
                failed_items.append(name)

        # 計算執行時間
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        # 檢查快取目錄大小
        cache_dir = PROJECT_DIR / "cache"
        cache_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
        cache_size_mb = cache_size / (1024 * 1024)

        print("\n" + "=" * 70)
        print(f"✅ 快取更新完成！")
        print(f"📊 成功: {success_count}/{len(data_items)}")
        if failed_items:
            print(f"⚠️  失敗項目: {', '.join(failed_items)}")
        print(f"💾 快取大小: {cache_size_mb:.1f} MB")
        print(f"⏱️  執行時間: {elapsed:.1f} 秒")
        print(f"⏰ 完成時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        return 0 if success_count == len(data_items) else 1

    except Exception as e:
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        print("\n" + "=" * 70)
        print(f"❌ 快取更新失敗: {e}")
        print(f"⏱️  執行時間: {elapsed:.1f} 秒")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
