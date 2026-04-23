# edge-ai-papers

一個把 **Edge AI / Edge AI Security / Embedded Systems Security** 論文，自動整理成 **繁體中文報告網站** 的 repo。

目前 repo 同時包含兩部分：

1. **靜態網站前端**：用 `reports/` 下的 markdown 與 index JSON 產生可瀏覽的論文報告網站。
2. **自動化產線腳本**：挑選論文、呼叫 NotebookLM 生成報告與影片、上傳 YouTube、再把結果發佈回這個 repo。

線上站點：<https://edge-ai-papers.openclaw572.workers.dev/>

---

## Repo 內容

```text
.
├── index.html              # 靜態網站入口
├── css/                    # 前端樣式
├── js/                     # 前端邏輯，讀取 reports/index.json 與每日 index
├── prompts/                # NotebookLM 查詢 prompt（review / general）
├── reports/                # 已發佈的論文報告與索引
├── scripts/                # 自動化產線腳本
├── backups/                # cron / pipeline 備份包（本機工作檔）
└── tmp/                    # 產線暫存輸出（本機工作檔）
```

---

## 網站怎麼運作

前端是純靜態頁面：

- `index.html` 載入 `js/app.js`
- `js/app.js` 先讀 `reports/index.json`
- 再依日期讀 `reports/YYYY-MM-DD/index.json`
- 點選論文後載入對應 markdown 檔並渲染
- 站上把論文分成兩類：
  - `Review Paper`
  - `General Paper`

也就是說，**只要把新的報告 markdown 與 index JSON 正確寫進 `reports/`，網站就會自動顯示新內容**。

---

## `reports/` 資料格式

### 全域索引

`reports/index.json` 會記錄：

- 最新更新日期 `lastUpdated`
- 每個日期批次的摘要
- 每批的 paper 類型（`review` / `general`）

### 每日索引

每個日期資料夾底下會有 `index.json`，例如：

- `reports/2026-04-23/index.json`

內容包含：

- `date`
- `paperCount`
- `paperType`
- `papers[]`
  - `id`
  - `category`
  - `title`
  - `path`
  - `link`
  - `type`
  - `youtubeUrl`（如果有）
- `notebookLM`
- `generatedAt`

markdown 報告檔則直接放在同一層，例如：

- `reports/2026-04-23/edge-ai-in-edge-ai-intelligentizing-mobile-edge-computing.md`

---

## 主要腳本

### 1. `scripts/run_notebooklm_pipeline.py`

整條 end-to-end pipeline 的主腳本，負責：

- 搜尋 / 篩選論文
- 預設優先找 `review` 論文，可切成 `general`
- 可選擇加強偏好正式期刊 / 頂會（`--prefer-top-tier`）
- 呼叫 NotebookLM 產生報告與影片
- 必要時做繁中後處理
- 呼叫 YouTube 上傳腳本
- 呼叫發佈腳本，把結果寫進 `reports/`

CLI：

```bash
python3 scripts/run_notebooklm_pipeline.py --help
```

目前支援的主要參數：

```bash
--mode {review,general}
--selection-mode {standard,full}
--topics TOPICS
--run-date RUN_DATE
--workspace WORKSPACE
--profiles PROFILES
--max-parallel MAX_PARALLEL
--discover-only
--skip-youtube
--skip-push
--prefer-top-tier
```

### 可開關功能（Feature Toggles）

先看最重要的預設行為：

- 預設 **跑 review paper**，不是 general paper
- 預設 **會上傳 YouTube**
- 預設 **會 push 回 GitHub**
- 預設 **不開啟 top-tier venue 強偏好**
- 預設 **不是 discover-only 模式**，會跑完整條 pipeline
- `run_scheduled_pipeline.sh` 的預設平行數是 **2**

這個 repo 目前已經有幾個可以直接切換的功能：

| 功能 | 開關方式 | 預設值 | 說明 |
|---|---|---:|---|
| 論文類型切換 | `--mode review` / `--mode general` | `review` | 預設優先找 review / survey；只有明確指定時才切 general paper。 |
| 論文選擇深度 | `--selection-mode standard` / `--selection-mode full` | 依腳本預設 | 控制候選論文選擇策略的深度。 |
| 主題切換 | `--topics edge-ai,edge-ai-security,embedded-security` | 三個主題全開 | 可以只跑指定主題，而不是每次都跑完整三類。 |
| 只做論文發現，不進 NotebookLM / 發佈 | `--discover-only` | 關 | 只做搜尋 / 篩選，不繼續後面的生成與發佈流程。 |
| 是否上傳 YouTube | `--skip-youtube` | 開 | 加上此旗標後會跳過 YouTube 上傳。 |
| 是否 push 回 GitHub | `--skip-push` | 開 | 加上此旗標後會跳過 git push。 |
| 是否加強偏好正式期刊 / 頂會 | `--prefer-top-tier` | 關 | 開啟後會更強烈偏向正式期刊與頂會來源；預設關閉。 |
| 並行數 | `--max-parallel N` | `2`（wrapper 預設） | 控制同時處理的平行工作數量。 |
| NotebookLM browser profile | `--profiles ...` | 腳本內建預設 | 可切換不同 NotebookLM 瀏覽器 profile。 |

如果你是用排程 wrapper：`scripts/run_scheduled_pipeline.sh`，對應的可切換功能如下：

| 功能 | 環境變數 | 預設值 | 說明 |
|---|---|---:|---|
| 論文類型 | `PAPER_MODE=review` / `PAPER_MODE=general` | `review` | 排程模式下最常用的主開關。 |
| 是否跳過 YouTube | `SKIP_YOUTUBE=1` | `0` | 設成 `1` 就不做 YouTube upload。 |
| 是否跳過 Git push | `SKIP_PUSH=1` | `0` | 設成 `1` 就不 push。 |
| 是否偏好 top-tier venue | `PREFER_TOP_TIER=1` | `0` | 設成 `1` 時啟用強偏好正式期刊 / 頂會。 |
| 執行日期 | `RUN_DATE=YYYY-MM-DD` | 今天 | 可覆寫輸出批次日期。 |
| 工作目錄 | `WORKSPACE=/tmp/...` | `/tmp/edge-ai-pipeline-$RUN_DATE` | 指定 pipeline 暫存工作區。 |
| 平行數 | `MAX_PARALLEL=N` | `2` | 控制平行處理數量。 |

### 2. `scripts/run_scheduled_pipeline.sh`

排程用 wrapper，會把環境變數轉成 `run_notebooklm_pipeline.py` 參數。

支援的環境變數：

- `PAPER_MODE`：`review` 或 `general`，預設 `review`
- `RUN_DATE`
- `WORKSPACE`
- `MAX_PARALLEL`
- `SKIP_YOUTUBE=1`
- `SKIP_PUSH=1`
- `PREFER_TOP_TIER=1`

範例：

```bash
PAPER_MODE=review RUN_DATE=$(date +%F) ./scripts/run_scheduled_pipeline.sh
```

### 3. `scripts/upload_youtube_batch.py`

把 NotebookLM 生成的影片上傳到 YouTube。

支援兩種模式：

- 單支影片上傳
- 根據 manifest 批次上傳

CLI：

```bash
python3 scripts/upload_youtube_batch.py --help
```

常見用法：

```bash
python3 scripts/upload_youtube_batch.py --channel-info

python3 scripts/upload_youtube_batch.py \
  --manifest /tmp/batch.json \
  --privacy-status unlisted \
  --write-back
```

### 4. `scripts/publish_notebooklm_batch.py`

把產線輸出的 manifest 發佈成網站可讀格式，會：

- 建立 `reports/YYYY-MM-DD/`
- 複製 markdown
- 追加影片區塊（若有 YouTube URL）
- 生成每日 `index.json`
- 更新全域 `reports/index.json`

CLI：

```bash
python3 scripts/publish_notebooklm_batch.py /path/to/manifest.json
```

### 5. Playwright / NotebookLM 輔助腳本

- `scripts/notebooklm_export_report_markdown.js`
- `scripts/notebooklm_delete_notebook.js`

這兩支是 browser automation 腳本，用來處理某些 NotebookLM 匯出 / 刪除流程。

---

## 產線流程概念

目前 repo 內的自動化流程大致是：

1. 選 3 個主題的論文：
   - `edge-ai`
   - `edge-ai-security`
   - `embedded-security`
2. 用 NotebookLM 生成繁中報告與影片摘要
3. 上傳影片到 YouTube
4. 把 markdown + index 發佈到 `reports/`
5. 由靜態網站直接讀取最新內容

---

## 本機執行需求

這個 repo 不是一個「單純 clone 後就能立即跑」的通用專案；它依賴作者本機的 Hermes / NotebookLM / Google OAuth 環境。

至少包含以下外部依賴：

- Python 3
- Google API Python 套件（YouTube upload 會用到）
- 可選的繁中後處理套件：
  - `opencc`
  - `deep-translator`
- Playwright（Node.js）
- 已登入 / 可用的 NotebookLM 瀏覽器 profile
- Google OAuth token：`~/.hermes/google_token.json`
- Hermes 相關腳本 / skill / browser profile（腳本內有讀取 `~/.hermes/...` 路徑）

> 注意：`scripts/run_notebooklm_pipeline.py` 目前明確依賴本機 `~/.hermes` 下的 skill、script、browser profile 與 token，因此它比較像是這個部署環境的 pipeline，而不是獨立套件。

---

## 快速使用

### 只看網站內容

直接打開：

- `index.html`
- 或部署後的網站 URL

### 只更新網站資料

如果你已經有 manifest：

```bash
python3 scripts/publish_notebooklm_batch.py /path/to/manifest.json
```

### 跑完整排程 pipeline

```bash
./scripts/run_scheduled_pipeline.sh
```

或：

```bash
PAPER_MODE=general PREFER_TOP_TIER=1 ./scripts/run_scheduled_pipeline.sh
```

---

## 已發佈內容

已發佈的報告都在 `reports/`，例如：

- `reports/2026-04-23/`
- `reports/2026-04-22/`
- `reports/2026-04-21/`

全域索引：

- `reports/index.json`

---

## 備註

- repo 內 `backups/`、`tmp/`、`scripts/__pycache__/` 目前偏向本機工作產物，不一定是網站運作必需。
- `scripts/run-paper-research.sh` 是較早期的舊流程腳本；目前主流程以 `run_notebooklm_pipeline.py` / `run_scheduled_pipeline.sh` 為主。
- YouTube 影片連結會被寫回 markdown 末尾的 `### 影片報告` 區塊。

---

## 後續可補強

如果之後要把這個 repo 做成更容易重現的公開專案，建議再補：

- `requirements.txt` / `pyproject.toml`
- `.gitignore`
- manifest schema 範例
- 部署方式（Cloudflare Pages / Workers 等）
- NotebookLM / Google / YouTube 憑證設定流程
