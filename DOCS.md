# Squeeze CN Screener 技術文件 v1.2.1 (China Market)

## 專案概述
本專案是一個基於 Python 的自動化股市掃描系統，旨在透過 Squeeze Momentum (擠壓動能) 指標及進階形態識別，篩選出具備爆發潛力的交易標的。支援中國 A 股市場，涵蓋上海主板、科創板、深圳主板與創業板。

## Ticker Universe Source
*   **Primary**: Eastmoney public quote list API.
*   **Secondary**: Bundled China A-share snapshot shipped in the package.
*   **Fallback Behavior**: If the primary source fails due to DNS/network issues, the screener falls back to the bundled snapshot so local scans can still run.

## 技術指標定義

### 1. Squeeze Momentum (TTM Squeeze)
*   **Squeeze ON (擠壓中)**: 當布林帶 (Bollinger Bands, 20, 2.0) 完全進入肯特納通道 (Keltner Channels, 20, 1.5) 內部時觸發。代表市場波動率極低，能量正在累積。
*   **Squeeze Fired (突破)**: 當布林帶穿出肯特納通道時觸發，預示單邊行情開啟。
*   **能量等級 (Energy Level)**: 
    *   計算公式: `(KC_Width - BB_Width) / KC_Width`
    *   等級: 0 (無擠壓) 到 3 (強烈擠壓 ★★★)。

### 2. 動能柱狀圖 (Momentum Histogram)
*   **青色 (Cyan)**: 動能向上且持續增強。
*   **深藍 (Blue)**: 動能向上但開始減弱。
*   **紅色 (Red)**: 動能向下且持續增強。
*   **栗色 (Maroon)**: 動能向下但開始減弱。

## 核心形態識別

### 1. 后羿射日 (Houyi Shooting Sun)
專為捕捉「強勢股回檔」設計：
*   前段漲幅 > 20%。
*   回檔至 0.5 - 0.618 斐波那契支撐區。
*   出現「長上影線」且伴隨 Squeeze ON 狀態。

### 2. 大鯨魚交易 (Whale Trading)
多時區共振形態：
*   日線 (Daily) 與週線 (Weekly) 同時處於 Squeeze ON。
*   雙時區動能均大於 0。

## 視覺化與報告

### 圖表標註說明
*   **黑色正方形 (⬛)**: 顯示於動能面板零軸下方，表示 **Squeeze ON**。
*   **淺灰色正方形 (⬜)**: 表示 **Squeeze OFF**。
*   **位置**: 統一固定於零軸下方，避免與動能柱狀圖重疊。

### 通知系統
*   **HTML Email**: 包含格式化表格，區分紅/綠漲跌配色。
*   **附件**: 自動夾帶 Top 15 潛力標的的 PNG 線圖。
*   **LINE 通知**: 即時發送掃描摘要與績效追蹤概況。

## 績效追蹤與策略檢視

### 追蹤欄位
`recommendations.csv` 現在會額外保存：
*   `pattern`
*   `momentum`
*   `prev_momentum`
*   `energy_level`
*   `squeeze_on`
*   `fired`
*   `market_regime`
*   `benchmark_ticker`
*   `strategy_return_pct`

### 保留規則
*   `tracking` 中的主動追蹤資料仍限制為最新 25 筆。
*   `completed` 的歷史資料會保留，供後續檢視策略是否需要修正。

### 分析命令
```bash
python3 scripts/analyze_tracking.py --csv recommendations.csv
PYTHONPATH=src python3 -m squeeze.cli analyze-tracking --csv recommendations.csv
```

## 檔案結構
*   `src/squeeze/data/`: 數據抓取邏輯 (Eastmoney, yfinance, fallback snapshot)。
*   `src/squeeze/engine/`: 核心運算引擎 (Indicators, Patterns)。
*   `src/squeeze/report/`: 報告生成與通知 (Jinja2, SMTP, LINE)。
*   `scripts/run_daily_scan.sh`: 中國雲每日掃描入口。
*   `scripts/upload_exports_to_oss.sh`: 匯出結果同步到 OSS。
*   `scripts/prune_old_exports.sh`: 清理過舊本機匯出目錄。
*   `deploy/systemd/`: `systemd` 的 service/timer 範本。
*   `.env.example`: ECS 環境變數範本。
*   `recommendations.csv`: 追蹤資料庫 (固定追蹤最新 25 檔)。

## 中國雲部署建議
第一版建議使用：
*   `ECS`: 執行 Python 專案與排程。
*   `cron`: 觸發每日掃描與上傳流程。
*   `OSS`: 保存 `exports/YYYY-MM-DD/...` 的歷史輸出。
*   `SLS`: 收集掃描日誌與錯誤訊息。

完整部署步驟與環境變數定義見 [DEPLOY_CN.md](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/DEPLOY_CN.md)。
