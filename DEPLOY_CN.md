# Squeeze CN 中國雲部署指南

本文件提供一版偏實務、方便除錯的部署方案：`ECS + cron + OSS + SLS`。

## 架構

```text
Alibaba Cloud China Region
├─ ECS
│  ├─ /opt/squeeze-cn-screener
│  ├─ .venv
│  ├─ exports/
│  ├─ logs/
│  └─ cron
├─ OSS
│  └─ squeeze-cn/exports/YYYY-MM-DD/
└─ SLS
   └─ daily scan logs
```

## 適用情境

適合目前這個專案的原因：
- 你還在調整 A 股資料源與 fallback。
- `ECS` 比 serverless 更容易檢查套件、快取、暫存檔與網路。
- 後續若流程穩定，再改成 `Function Compute` 定時觸發也不晚。

## 建議目錄

```text
/opt/squeeze-cn-screener
├─ src/
├─ scripts/
├─ exports/
├─ logs/
├─ data/
│  ├─ cache/
│  └─ snapshots/
├─ recommendations.csv
└─ .venv/
```

## 伺服器初始化

```bash
sudo mkdir -p /opt/squeeze-cn-screener
sudo chown "$USER" /opt/squeeze-cn-screener
git clone <YOUR_REPO_URL> /opt/squeeze-cn-screener
cd /opt/squeeze-cn-screener
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
mkdir -p exports logs data/cache data/snapshots
```

## 必要環境變數

`scripts/run_daily_scan.sh` 與 `scripts/upload_exports_to_oss.sh` 支援以下變數：

```bash
export SQUEEZE_CN_HOME=/opt/squeeze-cn-screener
export SQUEEZE_CN_PYTHON=/opt/squeeze-cn-screener/.venv/bin/python
export SQUEEZE_CN_LIMIT=300
export OSS_BUCKET=your-oss-bucket
export OSS_PREFIX=squeeze-cn/exports
export OSSUTIL_BIN=/usr/local/bin/ossutil
```

你也可以直接從 [.env.example](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/.env.example) 複製成 `/opt/squeeze-cn-screener/.env`。

## 每日掃描

手動執行：

```bash
cd /opt/squeeze-cn-screener
./scripts/run_daily_scan.sh
```

腳本會：
1. 建立 `logs/` 與 `exports/`
2. 啟用虛擬環境對應的 Python
3. 執行 `squeeze-cn scan --export`
4. 將 stdout/stderr 追加到 `logs/daily_scan.log`

## 上傳到 OSS

```bash
cd /opt/squeeze-cn-screener
OSS_BUCKET=your-oss-bucket ./scripts/upload_exports_to_oss.sh
```

預設會同步整個 `exports/` 到：

```text
oss://$OSS_BUCKET/$OSS_PREFIX/
```

## 清理舊匯出

預設保留 30 天：

```bash
cd /opt/squeeze-cn-screener
./scripts/prune_old_exports.sh
```

也可自訂：

```bash
RETENTION_DAYS=14 ./scripts/prune_old_exports.sh
```

## cron 建議

以下範例在每個交易日傍晚跑掃描、上傳、清理：

```cron
15 18 * * 1-5 cd /opt/squeeze-cn-screener && ./scripts/run_daily_scan.sh
25 18 * * 1-5 cd /opt/squeeze-cn-screener && OSS_BUCKET=your-oss-bucket ./scripts/upload_exports_to_oss.sh
40 18 * * 1-5 cd /opt/squeeze-cn-screener && RETENTION_DAYS=30 ./scripts/prune_old_exports.sh
```

## systemd 方案

如果你不想用 `cron`，也可以改用 repo 內建的 `systemd` 範本：

- [squeeze-cn-scan.service](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/deploy/systemd/squeeze-cn-scan.service)
- [squeeze-cn-scan.timer](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/deploy/systemd/squeeze-cn-scan.timer)
- [squeeze-cn-upload-exports.service](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/deploy/systemd/squeeze-cn-upload-exports.service)
- [squeeze-cn-upload-exports.timer](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/deploy/systemd/squeeze-cn-upload-exports.timer)
- [squeeze-cn-prune-exports.service](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/deploy/systemd/squeeze-cn-prune-exports.service)
- [squeeze-cn-prune-exports.timer](/Users/mingyenlin/Documents/GWork/mylin102/squeeze-cn-screener/deploy/systemd/squeeze-cn-prune-exports.timer)

安裝方式：

```bash
sudo cp deploy/systemd/*.service deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now squeeze-cn-scan.timer
sudo systemctl enable --now squeeze-cn-upload-exports.timer
sudo systemctl enable --now squeeze-cn-prune-exports.timer
```

這組 service 會從 `/opt/squeeze-cn-screener/.env` 讀取環境變數。

## 日誌與監控

- 本機日誌檔：`logs/daily_scan.log`
- 建議再把 `logs/` 收進阿里雲 `SLS`
- 若 `run_daily_scan.sh` 非零退出，應加告警

## 目前已知限制

- 中國市場 `ticker universe` 已有內建快照 fallback。
- 真正穩定性關鍵仍是 `market data` 網路可達性。
- 若你之後要做更穩的離線執行，建議補 `OHLCV` 本地快照層。
