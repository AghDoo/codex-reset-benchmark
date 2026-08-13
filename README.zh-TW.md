# Codex Reset Benchmark

[English](./README.md) | 繁體中文

獨立追蹤並比較社群 Codex Reset 預測準確度的 benchmark。

> **狀態：** 專案目前處於早期公開 benchmark 階段。所有預測都以發布當下的快照保存；在各時間尺度達到最低已結算樣本數前，排名僅屬暫定。

## 為什麼建立這個專案

目前已有多個獨立社群網站針對非固定排程的 Codex 用量重置發布機率或估計。本專案會在結果未知前保存這些公開預測，再依照一致、公開的事件定義結算結果，並用同一套可重現的方法評分。

Repository 本身就是 audit trail：GitHub Actions 會將 forecast snapshot 以 append-only NDJSON 保存；排行榜等衍生 JSON 則可以隨時由原始資料重新產生。

## 核心原則

- **As-issued evidence：** 評分網站當時真正發布的預測，不事後重建歷史。
- **共同 checkpoint：** 更新頻率高的網站不會因此取得較高權重。
- **機率預測評分：** Brier Score 為主指標；Calibration、Log Loss、二元 Hit Rate、樣本數與 availability 為輔助診斷。
- **不同 horizon 分開評分：** 5h、24h 與 48h 不混算。
- **只蒐集公開資料：** 不登入、不使用 cookies/credentials、不繞過 CAPTCHA、anti-bot 或其他防護，也不存取私人帳戶資料。
- **可重現：** 原始資料與評分程式公開，計算結果具 deterministic 特性。

## 目前評分尺度

| Horizon | 主指標 | 正式 checkpoints | 排名最低樣本 |
|---|---|---|---|
| 5h | Mean Brier Score ↓ | UTC 00:00、06:00、12:00、18:00 | 10 筆已結算預測 |
| 24h | Mean Brier Score ↓ | UTC 00:00、06:00、12:00、18:00 | 10 筆已結算預測 |
| 48h | Mean Brier Score ↓ | UTC 00:00、06:00、12:00、18:00 | 10 筆已結算預測 |

5h forecast 在 checkpoint 時必須是 1 小時內的 snapshot；24h 與 48h 可採用 6 小時內最新 snapshot。完整 horizon 尚未經過前不結算該筆預測。V1 完整支援 5h、24h、48h scoring；只是首批來源目前沒有可靠、可機器讀取的 5h forecast，因此 5h 初始樣本會是 0。

## Repository 結構

```text
.github/workflows/       CI、每小時蒐集、Pages 部署
src/codex_reset_benchmark/
                         collectors、storage、validation、scoring
scripts/                 CLI 入口
data/
  sources.json           資料來源 registry
  forecasts/             append-only 預測歷史
  events/resets.json     經審核的 Ground Truth
  status/                collector 健康狀態
docs/                    GitHub Pages 靜態網站
tests/                   單元測試
```

`data/` 是 audit/source layer；`docs/data/` 全部屬於可重新產生的 derived data。

## 本機開發

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/validate_data.py
python scripts/score.py
python scripts/build_site_data.py
```

執行一次公開來源蒐集：

```bash
python scripts/collect.py
```

新 snapshot 會寫入 `data/forecasts/YYYY/MM/DD.ndjson`。本專案不保存來源網站完整頁面，只保存正規化後的預測值、來源 URL、時間戳與內容雜湊等 provenance 資訊。

## 方法與資料模型

- [Benchmark methodology](./docs/reference-methodology.md)
- [資料 Schema](./docs/reference-data-schema.md)
- [資料來源盤點](./docs/reference-sources.md)
- [蒐集、更正與 opt-out 政策](./docs/reference-policies.md)

## GitHub Pages

靜態網站內容位於 `/docs`，對應目前 Repository 的 Pages source（`main:/docs`）。由於使用 `GITHUB_TOKEN` 的定時 workflow commit 不會觸發 branch-based Pages rebuild，線上 UI 會直接從 `raw.githubusercontent.com` 讀取 `main` 上最新的 generated JSON，並以已部署的 `/docs/data` 作為 fallback。

## 參與貢獻

請參考 [CONTRIBUTING.md](./CONTRIBUTING.md)。新增來源必須在公開頁面提供具有明確 horizon 的機率或估計值。需要登入、session cookie、CAPTCHA/anti-bot 繞過或侵入式爬取的來源不會納入。

## 免責聲明

本專案是獨立社群研究專案，與 OpenAI 或任何被追蹤的預測網站沒有從屬、贊助、背書或營運關係。「Codex」、「ChatGPT」及其他相關標誌之權利歸各自權利人所有。預測值屬實驗性估計，不應視為服務可用性或個人帳戶用量狀態的保證。

## 授權

本 Repository 的軟體程式碼使用 [MIT License](./LICENSE)。第三方事實、URL、名稱與公開預測數值仍受其來源可能適用的權利規範；本專案不主張擁有第三方服務或品牌。
