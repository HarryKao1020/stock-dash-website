# update_cache.py 更新日誌

## 最新版本功能

### ✅ 已實現功能

1. **日誌檔名格式化**
   - 格式: `YYYYMMDDHHMM_log.txt`
   - 範例: `202512290730_log.txt` (2025年12月29日 07:30 執行)
   - 每次執行產生獨立的日誌檔案，方便追蹤歷史記錄

2. **自動清理舊日誌**
   - 保留期限: 7 天
   - 每次執行時自動刪除超過 7 天的舊日誌
   - 清理記錄會寫入當次日誌

3. **詳細的更新記錄**
   - 執行日期和時間（含星期）
   - 日誌檔案名稱
   - 舊日誌清理結果
   - 所有 20 項資料更新狀態
   - 成功/失敗項目清單
   - 快取大小統計
   - 執行時間記錄

4. **補充遺漏的資料項**
   - 新增: 融資維持率 (`margin_maintenance_ratio`)
   - 總計: 20 項資料完整更新

## 日誌檔案範例

```
logs/
├── 202512220730_log.txt  # 2025-12-22 執行（7天前，會被清理）
├── 202512280730_log.txt  # 2025-12-28 執行（保留）
├── 202512290730_log.txt  # 2025-12-29 執行（保留）
└── README.md             # 日誌說明文件
```

## 使用方式

### 手動執行

```bash
# 本地環境
python3 scripts/update_cache.py

# Docker 環境
docker-compose exec web python scripts/update_cache.py
```

### Cron 排程

```bash
# 每個交易日早上 7:30 自動執行
30 7 * * 1-5 cd /path/to/project && docker-compose exec -T web python scripts/update_cache.py

# 或本地環境
30 7 * * 1-5 cd /path/to/project && python3 scripts/update_cache.py
```

## 查看日誌

```bash
# 查看最新日誌
cat $(ls -t logs/*_log.txt | head -1)

# 查看今天的日誌
cat logs/$(date +%Y%m%d)*_log.txt

# 查看所有成功項目
grep "成功更新項目" logs/*_log.txt -A 20

# 檢查失敗項目
grep "失敗" logs/*_log.txt

# 統計日誌數量
ls logs/*_log.txt | wc -l
```

## 自訂設定

### 調整保留天數

修改 [scripts/update_cache.py](update_cache.py) 第 88 行：

```python
cleanup_old_logs(days=7)  # 改成需要的天數，例如 days=14
```

### 修改日誌格式

修改第 39 行的 `strftime` 格式：

```python
# 目前格式: 202512290730_log.txt
LOG_FILENAME = datetime.now().strftime("%Y%m%d%H%M_log.txt")

# 範例: 只保留日期 (20251229_log.txt)
LOG_FILENAME = datetime.now().strftime("%Y%m%d_log.txt")

# 範例: 包含秒數 (20251229073001_log.txt)
LOG_FILENAME = datetime.now().strftime("%Y%m%d%H%M%S_log.txt")
```

## 測試

執行測試腳本（僅模擬，不會實際刪除）：

```bash
bash scripts/test_log_cleanup.sh
```

## 技術細節

- **日誌系統**: Python `logging` 模組
- **輸出位置**: 檔案 + 終端（雙重輸出）
- **字元編碼**: UTF-8
- **清理機制**: 基於檔案修改時間（mtime）
- **日誌等級**: INFO（一般訊息）、WARNING（警告）、ERROR（錯誤）

## 更新項目清單 (20 項)

1. 收盤價
2. 開盤價
3. 最高價
4. 最低價
5. 成交量
6. 成交金額
7. 融資餘額
8. 融資總餘額
9. 融資維持率 ✨ 新增
10. 大盤指數
11. 世界指數開盤
12. 世界指數收盤
13. 世界指數最高
14. 世界指數最低
15. 世界指數成交量
16. 處置股過濾
17. 警示股過濾
18. 當月營收
19. 營收YoY
20. 營收MoM
