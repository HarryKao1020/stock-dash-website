# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Dash-based Taiwan stock market dashboard** that provides real-time market data, technical analysis, and visualization tools. The application integrates with **FinLab** for historical data and **Shioaji** for real-time market data.

## Tech Stack

- **Framework**: Dash (Plotly) + Flask
- **UI**: Dash Bootstrap Components
- **Data Sources**:
  - FinLab API (historical stock data, company info, financial metrics)
  - Shioaji API (real-time market data for TSE/OTC indices)
- **Authentication**: OAuth2 (Google & Facebook) with Flask-Login + SQLAlchemy
- **Deployment**: Docker + Gunicorn

## Development Commands

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (with debug mode)
DEBUG=true PORT=8050 python app.py

# Run production mode locally
DEBUG=false python app.py
```

### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Data Warmup (避免首次載入緩慢)

```bash
# 手動觸發預熱 API
curl http://localhost:8050/api/warmup

# 或使用提供的腳本
./scripts/warmup.sh

# 設定 cron 自動預熱 (每個交易日早上 8:00)
# 編輯並安裝 crontab
cp scripts/crontab.example /tmp/stock-dash-cron
# 修改路徑後安裝
crontab /tmp/stock-dash-cron
# 驗證
crontab -l
```

### Environment Variables

Required environment variables in `.env`:

```bash
# FinLab & Shioaji API credentials
FINLAB_TOKEN=your_finlab_token
API_KEY=your_shioaji_api_key
SECRET_KEY=your_shioaji_secret_key

# Authentication (optional, see oauth.md for setup)
FLASK_SECRET_KEY=random_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
FACEBOOK_CLIENT_ID=your_facebook_client_id
FACEBOOK_CLIENT_SECRET=your_facebook_client_secret
LOGIN_REQUIRED=false  # Set to 'true' to require login

# Optional
DEBUG=true
PORT=8050
DB_DIR=/app/data  # For Docker deployments
```

## Architecture

### Application Structure

```
app.py                    # Main entry point, defines layout with sidebar navigation
├── auth.py              # OAuth authentication module (Google/Facebook)
├── finlab_data.py       # FinLab data management with Parquet caching & lazy loading
├── user_components.py   # User UI components for auth
├── pages/               # Multi-page Dash app
│   ├── home.py         # World indices dashboard
│   ├── realtime-market.py  # Real-time TSE/OTC market data
│   ├── kline.py        # Stock K-line (candlestick) charts
│   ├── treemap.py      # Sector treemap visualization
│   ├── margin-balance.py   # Margin trading balance analysis
│   ├── market-value-ranking.py  # Market cap rankings
│   ├── money-flow.py   # Money flow analysis
│   └── rev-rank.py     # Revenue growth rankings
└── data/
    ├── shioaji_data.py # Shioaji real-time data with 2-layer caching
    └── stock_group.json # Stock sector groupings
```

### Key Architecture Patterns

1. **Multi-page Navigation**: Uses Dash's `use_pages=True` with responsive sidebar (desktop) and offcanvas menu (mobile)

2. **Data Layer (finlab_data.py)**:
   - Global singleton pattern: `finlab_data = FinLabData(use_parquet=True)`
   - Lazy loading with `@property` decorators for each data type (only load when accessed)
   - Two-level caching: **Parquet files** (24hr cache, 5-10x smaller) + in-memory
   - **Cache update**: Managed by cron job (`scripts/update_cache.py`), NOT in-app auto-refresh
   - Primary data accessed: `finlab_data.close`, `finlab_data.volume`, `finlab_data.amount`, etc.

3. **Real-time Data (shioaji_data.py)**:
   - **Two-layer cache strategy**:
     - File cache: Historical data (before today) stored in `cache/shioaji/*.pkl`
     - Memory cache: Full dataset including today's real-time data
   - **Smart update logic**:
     - Historical data: Updates hourly (HISTORICAL_UPDATE_INTERVAL = 3600s)
     - Real-time data: Updates every 60s during trading hours (08:45-14:00)
   - Entry point: `get_cached_or_fetch(api)` returns (tse_df, otc_df)
   - Incremental updates: Only fetches new data since last cached date

4. **Authentication System**:
   - OAuth2 flow with Google/Facebook providers (authlib)
   - SQLite database for user storage (`data/users.db`)
   - Flask-Login for session management
   - Optional login requirement controlled by `LOGIN_REQUIRED` env var
   - Protected routes in `app.py` via `@server.before_request` decorator
   - See `oauth.md` for OAuth setup instructions

5. **Page Structure**: Each page in `pages/` follows pattern:
   ```python
   import dash
   from dash import callback, Input, Output

   dash.register_page(__name__, path="/page-url", name="Page Name")

   layout = html.Div([...])  # Page layout

   @callback(...)  # Callbacks for interactivity
   def update_data(...):
       ...
   ```

## Data Management

### FinLab Data Caching

- Cache directory: `cache/` (created automatically)
- Cache format: **Parquet** (`.parquet` files with built-in timestamps)
  - Fallback: Pickle format (`.pkl` + `.time` files) if Parquet fails
- Default cache validity: 24 hours (12 hours for some data)
- **Cache update method**: Cron job (recommended) or manual refresh

#### Cache Update Strategy

**Recommended: Cron Job (Production)**
```bash
# Setup cron to update cache daily at 7:30 AM (before market opens)
# See scripts/crontab.example for full setup

# Method 1: Local environment
30 7 * * 1-5 cd /path/to/project && python3 scripts/update_cache.py

# Method 2: Docker environment
30 7 * * 1-5 cd /path/to/project && docker-compose exec -T web python scripts/update_cache.py
```

**Alternative: Manual Refresh**
```python
# In Python console or script
from data.finlab_data import finlab_data
finlab_data.refresh()  # Force re-download all data
```

**Not Recommended: In-app Auto-refresh** (已移除)
- ❌ 舊方式: `start_auto_refresh(interval_hours=4)` in app.py
- ⚠️ 問題: 應用程式重啟會中斷、記憶體常駐、無法精確控制時間
- ✅ 改用: Cron job 排程更新（穩定、可控、獨立於應用程式）

#### Parquet Format Benefits

- **5-10x smaller file size**: ~813 MB → ~80-160 MB total cache
- **Column-based storage**: Faster partial reads for specific stocks
- **Cross-platform compatibility**: Works with DuckDB, Spark, R, etc.
- **No separate timestamp files**: Metadata embedded in Parquet files
- **Better compression**: Uses Snappy compression algorithm

**Switching back to Pickle** (if needed):
```python
# In data/finlab_data.py, modify line 882:
finlab_data = FinLabData(use_parquet=False)  # Use Pickle format
```

### Shioaji Data Caching

- Cache directory: `cache/shioaji/`
- Files: `TSE_historical.pkl`, `OTC_historical.pkl`
- **Historical data** (before today): Persistent file cache, only updated when new trading days exist
- **Today's data**: Always fetched via `api.snapshots()` during trading hours
- Performance: 10-100x faster than re-downloading on every request
- See `data/shioaji_data_README.md` for detailed caching mechanics

### Common Data Access Patterns

```python
from finlab_data import finlab_data

# Stock price data (lazy loaded, cached)
close = finlab_data.close          # DataFrame: dates x stock_ids
volume = finlab_data.volume
amount = finlab_data.amount

# Get stock info
stock_name = finlab_data.get_stock_name("2330")
stock_list = finlab_data.get_stock_list()  # Returns ["2330 台積電", ...]

# Margin trading data
margin_ratio = finlab_data.margin_maintenance_ratio
margin_balance = finlab_data.margin_balance

# World indices
world_data = finlab_data.get_world_index_data("^GSPC", days=360)

# Revenue rankings
df, date = finlab_data.get_revenue_ranking(sort_by="yoy", top_n=100)
```

## Working with This Codebase

### Adding a New Page

1. Create `pages/new_page.py`:
```python
import dash
from dash import html, callback, Input, Output

dash.register_page(__name__, path="/new-page", name="New Page")

layout = html.Div([...])

@callback(...)
def update_chart(...):
    ...
```

2. Add navigation link to `app.py` in `nav_links` list:
```python
{"icon": "fa-icon-name", "text": "New Page", "href": "/new-page"}
```

### Data Refresh Strategy

- **Development**: Use existing cache, set `start_auto_refresh(interval_hours=4)` in app.py
- **Production**: Cache persists in Docker volumes (`./cache:/app/cache`)
- **Force refresh**: Call `finlab_data.refresh()` or set environment variable to trigger on startup
- **Warmup API**: Use `/api/warmup` endpoint to preload all data into memory before first user access
  - Manual: `curl http://localhost:8050/api/warmup`
  - Automated: Set up cron job (see [scripts/crontab.example](scripts/crontab.example))
  - Recommended: Run warmup at 8:00 AM on trading days (Mon-Fri)

### Authentication

- Login is **optional** by default (controlled by `LOGIN_REQUIRED=false`)
- To protect pages: Check `current_user.is_authenticated` in callbacks or use `@require_login` decorator
- User database: SQLite at `data/users.db` (persisted in Docker volume)
- Admin panel: `/auth/admin/users` (requires `is_admin=True` in database)

### Performance Considerations

- Always use cached data access patterns (avoid re-fetching in callbacks)
- For Shioaji real-time data: `get_cached_or_fetch(api)` handles all caching automatically
- Dash callbacks: Use `prevent_initial_call=True` when appropriate
- Large DataFrames: Filter early (e.g., `.tail(100)`) before processing

### Docker Memory Limits

- Current limit: 1800M (configured for 2GB VPS)
- Reserved: 512M minimum
- If encountering OOM: Reduce cache sizes or filter data more aggressively

## API Credentials Setup

1. **FinLab**: Get token from https://ai.finlab.tw/ (VIP subscription required)
2. **Shioaji**: Register at https://sinotrade.github.io/
3. **OAuth** (optional): See `oauth.md` for Google/Facebook OAuth setup

## Common Troubleshooting

- **"資料不足"**: FinLab cache may be stale, call `finlab_data.refresh()`
- **First user loads slowly**: Data is fetched on-demand. Use warmup API (`/api/warmup`) or set up cron to preload data
- **Shioaji login fails**: Check API credentials in `.env`, ensure Shioaji API is accessible
- **OAuth redirect errors**: Verify callback URLs match exactly in Google/Facebook console
- **Database locked**: SQLite issue, ensure only one process accesses `data/users.db`
- **Cache directory permission errors**: Ensure app can write to `cache/` directory
