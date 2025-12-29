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
  30 7 * * 1-5 cd /path/to/project && docker-compose exec -T web python scripts/update_cache.py

  或本地環境：
  30 7 * * 1-5 cd /path/to/project && python3 scripts/update_cache.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# 加入專案路徑
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from data.finlab_data import finlab_data

# 設定日誌目錄和檔案
LOGS_DIR = PROJECT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# 使用當天日期作為日誌檔名 (格式: YYYYMMDDHHMM_log.txt)
LOG_FILENAME = datetime.now().strftime("%Y%m%d%H%M_log.txt")
LOG_FILE = LOGS_DIR / LOG_FILENAME

# 設定日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # 同時輸出到終端
    ]
)

def cleanup_old_logs(days=7):
    """清理 N 天前的舊日誌檔案"""
    from datetime import timedelta

    cutoff_time = datetime.now() - timedelta(days=days)
    deleted_count = 0

    for log_file in LOGS_DIR.glob("*_log.txt"):
        if log_file.is_file():
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    logging.info(f"🗑️  已刪除舊日誌: {log_file.name}")
                    deleted_count += 1
                except Exception as e:
                    logging.warning(f"⚠️  無法刪除 {log_file.name}: {e}")

    if deleted_count > 0:
        logging.info(f"✅ 共清理 {deleted_count} 個舊日誌檔案（超過 {days} 天）")
    else:
        logging.info(f"ℹ️  無需清理（沒有超過 {days} 天的日誌）")

def main():
    """執行快取更新"""
    start_time = datetime.now()

    logging.info("=" * 70)
    logging.info("🔄 FinLab 快取更新開始")
    logging.info(f"⏰ 開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"📅 更新日期: {start_time.strftime('%Y年%m月%d日 %A')}")
    logging.info(f"📝 日誌檔案: {LOG_FILENAME}")
    logging.info("=" * 70)

    # 清理 7 天前的舊日誌
    logging.info("🧹 檢查並清理舊日誌...")
    cleanup_old_logs(days=7)

    try:
        # 使用 global singleton（與應用程式共用同一實例）
        finlab = finlab_data

        # 強制刷新所有快取
        logging.info("🗑️  清除舊快取...")
        finlab.refresh()

        logging.info("📥 重新下載資料（Parquet 格式）...")

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
            ("融資維持率", lambda: finlab.margin_maintenance_ratio),
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

        logging.info(f"📊 預載 {len(data_items)} 項資料...")
        success_count = 0
        success_items = []
        failed_items = []

        for name, getter in data_items:
            try:
                data = getter()
                if data is not None:
                    if hasattr(data, 'shape'):
                        logging.info(f"   ✅ {name:<20} - 形狀: {data.shape}")
                    else:
                        logging.info(f"   ✅ {name:<20} - 已載入")
                    success_count += 1
                    success_items.append(name)
                else:
                    logging.warning(f"   ⚠️  {name:<20} - 資料為 None")
                    failed_items.append(name)
            except Exception as e:
                logging.error(f"   ❌ {name:<20} - 錯誤: {str(e)[:50]}")
                failed_items.append(name)

        # 計算執行時間
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        # 檢查快取目錄大小
        cache_dir = PROJECT_DIR / "cache"
        cache_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
        cache_size_mb = cache_size / (1024 * 1024)

        logging.info("=" * 70)
        logging.info("✅ 快取更新完成！")
        logging.info(f"📊 成功: {success_count}/{len(data_items)}")

        if success_items:
            logging.info(f"✅ 成功更新項目:")
            for item in success_items:
                logging.info(f"   - {item}")

        if failed_items:
            logging.warning(f"⚠️  失敗項目: {', '.join(failed_items)}")

        logging.info(f"💾 快取大小: {cache_size_mb:.1f} MB")
        logging.info(f"⏱️  執行時間: {elapsed:.1f} 秒")
        logging.info(f"⏰ 完成時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=" * 70)

        return 0 if success_count == len(data_items) else 1

    except Exception as e:
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        logging.error("=" * 70)
        logging.error(f"❌ 快取更新失敗: {e}")
        logging.error(f"⏱️  執行時間: {elapsed:.1f} 秒")
        logging.error("=" * 70)
        import traceback
        logging.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
