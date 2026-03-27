# Squeeze CN Screener v1.2.1

專為中國 A 股市場設計的自動化標的篩選工具，採用 Squeeze Momentum 擠壓動能邏輯與進階形態識別技術。對外命名與美股版 `squeeze-us`、台股版 `squeeze-tw` 對齊，中國市場命令統一為 `squeeze-cn`。

Ticker universe 採雙來源模式：
- 主來源：Eastmoney 即時股票列表
- 次來源：repo 內建的 A 股快照，供 DNS 或外網失敗時 fallback

## 核心功能
- **高效能掃描**：採用混合多執行緒 (I/O) 與多處理器 (CPU) 引擎，快速掃描中國 A 股 (上海主板、科創板、深圳主板、創業板)。
- **進階形態識別**：支援 TTM Squeeze、后羿射日 (Houyi Shooting Sun) 及大鯨魚交易 (Whale Trading) 形態。
- **明確交易信號**：每檔個股皆提供明確的操作建議，如「強烈買入 (爆發)」、「觀察 (跌勢收斂)」或「觀望」。
- **專業 HTML 報表**：自動生成美觀的 HTML 表格 Email，並夾帶 Top 15 潛力標的的 K 線分析圖。
- **自動化通知**：整合 LINE Bot 與 Email (SMTP) 通知，支援多收件人設定。
- **績效追蹤**：每日自動追蹤推薦標的的表現，資料庫自動維持在最新的 25 檔以內。
- **策略檢視**：保留完成追蹤的歷史資料，並可用分析命令檢查各類訊號、持有天數與市場 regime 的表現差異。

## 快速開始

### 安裝
```bash
pip install ./squeeze
```

### 執行掃描
```bash
# 掃描目前的擠壓動能標的，並生成圖表與發送通知
squeeze-cn scan --export --plot --notify
```

### 檢視策略績效
```bash
python3 scripts/analyze_tracking.py --csv recommendations.csv
PYTHONPATH=src python3 -m squeeze.cli analyze-tracking --csv recommendations.csv
```

## 中國雲部署
建議第一版先用 `ECS + cron + OSS + SLS`，把 daily scan、匯出、上傳與日誌拆開，方便除錯與維運。部署細節見 [DEPLOY_CN.md](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/DEPLOY_CN.md)。

專案已附上可直接調整的部署腳本：
- `scripts/run_daily_scan.sh`
- `scripts/upload_exports_to_oss.sh`
- `scripts/prune_old_exports.sh`

若你偏好 `systemd` 而不是 `cron`，專案也附上：
- `deploy/systemd/squeeze-cn-scan.service`
- `deploy/systemd/squeeze-cn-scan.timer`
- `deploy/systemd/squeeze-cn-upload-exports.service`
- `deploy/systemd/squeeze-cn-upload-exports.timer`
- `deploy/systemd/squeeze-cn-prune-exports.service`
- `deploy/systemd/squeeze-cn-prune-exports.timer`
