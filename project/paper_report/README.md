# Paper Report 專案

此專案位於 `~/.hermes/project/paper_report`，用來建立「領域相關論文自動挑選 → 繁體中文 Markdown / LaTeX 文字報告 → 影片報告 → GitHub / YouTube 發布 → 本地清理」的工作流。

> 維護規則：此 README 是本專案的主要狀態紀錄。之後若有新增功能、修改篩選規則、調整 API / rate limit、或補上尚未完成的模組，需同步更新 README，並在回覆中說明「已更新 README」。

---

## 目前狀態總覽

### 已完成

- 建立專案目錄與基本 Python package：`src/paper_report/`。
- 支援多領域 Research Profile：可新增、刪除、修改、查詢領域設定。
- Research Profile 支援 `paper_type`，預設為 `review`；若使用者特別指定一般研究論文，可設為 `general`，也可設為 `any` 做評估 / 除錯。
- 實作 Daily Paper Hunter MVP：
  - 優先搜尋最近 4 個月。
  - 最近 4 個月不足品質門檻時，才依序 fallback 到 4～12 個月前、13～36 個月前、36～60 個月前（最多回溯 5 年）。
  - 候選來源依序支援 `arXiv → Semantic Scholar → OpenAlex → Google Scholar`。
  - 每個來源抓完都會重新 normalize / dedupe / ranking / quality gate；足夠就停止，不足才查下一個來源。
  - 外部來源若 rate limited 或暫時失敗，workflow 會跳到下一個來源，避免 cron job 整體中斷。
- 實作候選論文正規化與去重：DOI → arXiv ID → Semantic Scholar ID → title normalized string。
- 實作 semantic relevance ranking，不只靠 keyword。
- 實作 anti-keyword-stuffing regression tests，避免 keyword-stuffed decoy 或高引用但不相關論文壓過真正相關論文。
- 實作 deterministic heuristic LLM Review placeholder，可之後替換成真實 LLM / NotebookLM。
- 實作 YouTube / GitHub / Codex Gmail 發布與任務串接：
  - `upload-videos` 會呼叫 OpenClaw CLI，要求 OpenClaw 用 webbridge 操作瀏覽器上傳影片到 YouTube；上傳前先用 image2.0 產生該論文專屬封面圖並在 YouTube Studio 設為 custom thumbnail；支援平行 worker，並把 `youtube_url` / `youtube_thumbnail_path` 回寫 manifest 與 Markdown。
  - `publish-github` 會把 `https://github.com/openclaw572/edge-ai-papers.git` 依原本靜態網站架構更新：保留 `index.html`、`css/`、`js/`、`reports/`，清掉舊的產線方法 / 任務說明與 README，改寫成只描述網站架構；再新增本 project 到 `project/paper_report/`，並把報告寫入 `reports/YYYY-MM-DD/` 與 index JSON。第一次正式執行也會先做這個 repo 清理 / 改寫並 push。
  - `record-references` 會在清理本地報告 / 影片前，查詢並記錄本次 selected papers 引用的 references，標明每筆 reference 是哪篇 selected paper 引用的。
  - `run-full-pipeline` 串起 hunt → generate reports/videos → record references → upload YouTube(+image2.0 thumbnail) → publish GitHub → 成功驗證後清理 generated artifacts → Codex CLI Gmail 通知。
- 實作報告生成 MVP：
  - 依找到 / 選出的論文數量 `floor(n / 2)` 分配給本地方法，其餘分配給 NotebookLM。
  - 本地方法會產生繁體中文 Markdown 報告與 `.mp4` 影片報告；影片使用 `ffmpeg`，可選 `edge-tts` 產生繁中旁白，失敗時保留可追蹤 placeholder / 靜音影片。
  - NotebookLM 路線已安裝 `notebooklm-mcp-cli`，並把 `notebooklm-mcp` 設為 Hermes MCP server（39 個工具已啟用；新 session 可直接使用）。
  - NotebookLM 生成流程透過同套 MCP/CLI 套件的 `nlm` automation：建立 notebook、加入 source、產生 Report、產生 Video Overview、下載 report/video。
  - NotebookLM 上傳或下載失敗時，會呼叫 OpenClaw CLI，要求它用 webbridge 操作 NotebookLM 網頁補上上傳 / 下載。
  - NotebookLM Video Overview 最多等待 30 分鐘；若只是尚未生成完成，會 fallback 到本地影片生成。
  - 本地影片腳本會依 `paper_type` 套用不同結構：review paper 10 段、一般 paper 12 段。
  - 多篇論文使用 `ThreadPoolExecutor` 平行處理，並輸出 `manifest.json`。
- 建立離線 fixture demo 與 pytest 測試。
- 已依官方文件調整 / 固定 request pacing：
  - arXiv：1 request / 3 seconds。
  - Semantic Scholar：採保守 1 request / second；支援 API key header。

### 未完成 / 待補

- NotebookLM 帳號登入 / cookie auth：目前 `nlm doctor` 顯示尚未登入；正式跑 NotebookLM 前需執行 `nlm login`。
- 本地全文 PDF 解析與更完整的章節式摘要：introduction / method / experiment / conclusion。
- LaTeX 報告輸出。
- 更精緻的本地影片報告：字幕、多頁 slide、Manim / slide renderer pipeline。
- 遠端驗證規則可再補強：目前 GitHub 以 commit / push 結果為準，YouTube 以 OpenClaw 回傳 URL 為準；後續可加入 URL live probe / YouTube processing status 檢查。
- 真實 LLM Review API 串接；目前是 deterministic heuristic reviewer。
- Google Scholar 官方 API 不存在；目前預留 SerpAPI 路線，需設定 API key 才會啟用。

---

## 目錄

```text
configs/
  research_profile.yaml        # 單一領域設定
  research_profiles.yaml       # 多領域 profile store，可新增/刪除/修改
fixtures/
  sample_candidates.yaml       # 離線測試候選論文
src/paper_report/
  arxiv_client.py              # arXiv API query / Atom parser
  semantic_scholar.py          # Semantic Scholar candidate search + metadata enrichment
  openalex.py                  # OpenAlex candidate search / abstract reconstruction
  google_scholar.py            # Google Scholar candidate search via SerpAPI
  source_utils.py              # candidate source order / query / date helpers
  ranking.py                   # vector relevance + metadata scoring
  workflow.py                  # windows、quality gate、fallback、selection
  report.py                    # 繁體中文 Markdown report
  report_generation.py         # 本地/NotebookLM 報告與影片生成、OpenClaw fallback、平行 orchestration
  youtube_openclaw.py          # OpenClaw CLI + webbridge YouTube 上傳、image2.0 封面、manifest/Markdown 回寫
  github_publish.py            # edge-ai-papers 靜態網站 repo 清理、報告發布、project 複製、git commit/push
  references.py                # selected papers reference 紀錄（刪除本地產物前執行）
  codex_notify.py              # 任務完成/失敗後使用 Codex CLI 寄 Gmail 通知
  pipeline.py                  # hunt → generate → references → YouTube → GitHub → cleanup → email 串接 runner
  cli.py                       # profiles / hunt / generate-reports / upload / publish / full pipeline CLI
tests/
  test_*.py                    # pytest 測試
docs/
  report_generation_and_delivery_plan.md
  harness_pipeline_pseudo.yaml
outputs/
  daily_report.md              # 執行後產生
  daily_report.json            # 執行後產生
```

---

## 安裝 / 測試

```bash
cd ~/.hermes/project/paper_report
python -m pip install -r requirements.txt
PYTHONPATH=src pytest -q
```

離線 demo，不打外部 API，使用 fixture 驗證 fallback 與報告輸出：

```bash
cd ~/.hermes/project/paper_report
PYTHONPATH=src python -m paper_report.cli hunt \
  --profile configs/research_profile.yaml \
  --sample-candidates fixtures/sample_candidates.yaml \
  --today 2026-05-26 \
  --output outputs/daily_report.md
```

---

## Live multi-source run

預設候選來源順序：

```text
arxiv,semantic_scholar,openalex,google_scholar
```

執行：

```bash
cd ~/.hermes/project/paper_report
PYTHONPATH=src python -m paper_report.cli hunt \
  --profile configs/research_profile.yaml \
  --output outputs/daily_report.md
```

---

## 生成 Markdown / 影片報告

先跑 `hunt` 產生 `outputs/daily_report.json`，再執行：

```bash
cd ~/.hermes/project/paper_report
PYTHONPATH=src python -m paper_report.cli generate-reports \
  --input outputs/daily_report.json \
  --output-dir outputs/generated_reports \
  --max-workers 4
```

分配規則：

```text
本地方法數量 = floor(selected_papers_count / 2)
NotebookLM 方法數量 = selected_papers_count - 本地方法數量
```

輸出：

```text
outputs/generated_reports/
  local/<paper>/report.md
  local/<paper>/video.mp4
  notebooklm/<paper>/report.md
  notebooklm/<paper>/video.mp4
  manifest.json
```

NotebookLM / MCP 安裝與設定狀態：

```bash
uv tool install notebooklm-mcp-cli
hermes mcp add notebooklm --command notebooklm-mcp
hermes mcp list
```

已完成安裝與 Hermes MCP server 設定；但 NotebookLM 正式操作需要 Google cookie auth，目前需手動登入一次：

```bash
nlm login
nlm doctor
```

NotebookLM 影片生成等待策略：

```text
--video-wait-timeout-seconds 1800  # 預設 30 分鐘
```

如果 NotebookLM video overview 超過時間仍未完成，且不是下載錯誤，就改用本地 `ffmpeg` 影片生成。

本地影片腳本會依 `paper_type` 分流：

- Review paper：開場、研究背景、Review 範圍、分類架構、各類方法重點、比較與趨勢、挑戰與限制、未來方向、你的觀點、總結。
- 一般 paper：開場、研究問題、背景與動機、相關工作簡述、核心方法、系統/模型架構、實驗設計、實驗結果、優點與貢獻、限制與問題、你的觀點、總結。

可手動改來源順序或暫時只跑部分來源：

```bash
PYTHONPATH=src python -m paper_report.cli hunt \
  --profile configs/research_profile.yaml \
  --candidate-sources arxiv,semantic_scholar,openalex \
  --output outputs/daily_report.md
```

---

## API rate limit / request pacing

### arXiv

官方文件：

- https://info.arxiv.org/help/api/tou.html
- https://info.arxiv.org/help/api/user-manual.html

目前設定：

```text
ARXIV_REQUEST_INTERVAL_SECONDS = 3.0
```

原因：arXiv Terms of Use 要求 legacy APIs，包括 arXiv API，不超過每 3 秒 1 個 request，且一次只用單一連線。

CLI 預設：

```text
--arxiv-sleep-seconds 3.0
```

### Semantic Scholar

官方文件：

- https://www.semanticscholar.org/product/api

官方頁面目前描述：

- 大多數 endpoint 可無 API key 使用，但 unauthenticated users 共用 public rate limit pool，文件寫為 shared 1000 requests / second，且 heavy use 時可能被進一步 throttle。
- API key 的 introductory rate limit 是 1 RPS on all endpoints。

本專案採保守設定：

```text
SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS = 1.0
```

原因：

- 這符合 API key introductory rate limit：1 request / second。
- 即使未設定 API key，也避免對 shared unauthenticated pool 造成壓力。
- 實測 Semantic Scholar 可能回 HTTP 429，所以 workflow 會在該來源失敗時跳到 OpenAlex / 後續來源。

CLI 預設：

```text
--semantic-sleep-seconds 1.0
```

可設定 API key：

```bash
export SEMANTIC_SCHOLAR_API_KEY="你的_key"
# 或
export S2_API_KEY="你的_key"
```

程式會自動把 key 放入 `x-api-key` header。

### OpenAlex

官方 API 不需 key；建議設定 mailto 方便 OpenAlex 聯絡與識別用戶：

```bash
export OPENALEX_MAILTO="you@example.com"
```

目前預設：

```text
--openalex-sleep-seconds 0.2
```

### Google Scholar

Google Scholar 沒有官方免費 JSON API，直接 scraping 容易遇到 CAPTCHA，也不適合作為穩定 cron pipeline。

目前補法：使用 SerpAPI 的 Google Scholar engine。

啟用方式：

```bash
export SERPAPI_API_KEY="你的_key"
# 或
export GOOGLE_SCHOLAR_SERPAPI_KEY="你的_key"
```

如果沒有 key：

```text
Google Scholar source 會安全回傳空候選，不會讓 workflow 失敗。
```

---

## 論文篩選規則詳細說明

### 1. Research Profile

每個領域由 profile 定義，例如：

```yaml
topic_name: "AI Agent Coordination and File-based Collaboration"
paper_type: "review"   # 預設找 review paper；若要一般 paper，改成 "general"
description: "..."
positive_seed_papers: []
positive_keywords: []
negative_keywords: []
arxiv_categories: []
prefer_full_text: true
search_policy: {...}
quality_threshold: {...}
```

用途：

- `paper_type`：預設 `review`，會讓候選 query 加入 review / survey intent，並讓 quality gate / final selection 優先選 review paper；若指定 `general`，則改優先一般研究論文；`any` 主要供測試或除錯。
- `description`：semantic relevance 的主要比較對象。
- `positive_seed_papers`：作為 seed similarity 的比較基準。
- `positive_keywords`：只用於候選召回與弱 ranking feature，不作為最終選擇主因。
- `negative_keywords`：用於排除相近但錯誤的領域，例如 robot swarm / traffic control。
- `arxiv_categories`：arXiv candidate search 的類別限制。

### 2. 時間窗策略

先跑 primary window：

```text
recent_0_to_4_months
```

若最近 4 個月 qualified papers 不足 `min_papers_required`，才依序 fallback：

```text
fallback_4_to_12_months
fallback_13_to_36_months
fallback_36_to_60_months
```

每篇論文都會標示 `time_window`，報告也會透明列出 fallback 是否被使用。

### 3. 候選來源補法

每個時間窗內的候選補法如下：

```text
arXiv
  ↓ 如果 quality gate 不足
Semantic Scholar
  ↓ 如果 quality gate 不足 / Semantic Scholar 429 或失敗
OpenAlex
  ↓ 如果 quality gate 不足
Google Scholar via SerpAPI
```

重點：

- 每補一個來源，都會合併目前候選、去重、重新 ranking、重新 quality gate。
- 一旦達到品質門檻，就不再查後面的來源。
- 只有當較新的時間窗所有來源都不足，才進入較舊 fallback window。

### 4. 去重規則

去重順序：

```text
1. DOI
2. arXiv ID
3. Semantic Scholar paperId
4. normalized title
```

合併 metadata 時：

- 較長 abstract 優先保留。
- DOI / URL / PDF / IDs 等缺欄會由後來來源補上。
- authors / categories 會合併去重。

### 5. Semantic relevance

目前使用本地 deterministic semantic-ish vector：

- tokenization
- domain synonym expansion
- hashed embedding
- cosine similarity

比較對象：

```text
profile_similarity = similarity(paper.title + abstract, profile.description)
seed_similarity = max similarity against positive_seed_papers
positive_keyword_score = exact positive keyword weak signal
negative_keyword_penalty = negative keyword + negated domain evidence penalty
```

語意相關性：

```text
semantic_relevance = scaled(
  0.70 * profile_similarity
+ 0.25 * seed_similarity
+ 0.05 * positive_keyword_score
- negative_keyword_penalty
)
```

注意：`positive_keyword_score` 權重只有 0.05，刻意避免「塞滿 keyword 的假相關論文」被選上。

### 6. metadata scoring

最終 ranking score：

```text
final_score =
  0.45 * semantic_relevance
+ 0.20 * recency_score
+ 0.15 * full_text_score
+ 0.10 * citation_signal
+ 0.10 * code_or_project_signal
```

各分數：

- `recency_score`
  - recent 0～4 months：1.0
  - fallback 4～12 months：0.7
  - fallback 13～36 months：0.4
  - fallback 36～60 months：0.2
  - older / unknown：0.2
- `full_text_score`
  - 有 PDF：1.0
  - open access landing page：0.7
  - DOI / abstract only：0.3
  - 無法取得：0.0
- `citation_signal`
  - 使用 citation_count + influential_citation_count 的 log scaling。
  - 只佔 0.10，避免高引用但不相關論文壓過語意相關論文。
- `code_or_project_signal`
  - 若偵測到 GitHub / source code / dataset / project page，給加分。

### 7. Quality Gate

預設門檻：

```yaml
quality_threshold:
  min_final_score: 0.72
  min_relevance_score: 0.75
  min_papers_required: 3
  max_papers_to_output: 5
```

Qualified paper 條件：

```text
final_score >= min_final_score
and semantic_relevance >= min_relevance_score
```

如果最近 4 個月 qualified papers 數量未達 `min_papers_required`，才啟動 fallback。

### 8. LLM Review placeholder

目前 `review.py` 使用 deterministic heuristic reviewer，只審 ranking 後 Top 20。

之後可替換成：

- 真實 LLM API。
- NotebookLM Reports 結果。
- 混合 reviewer：LLM relevance / novelty / practical value + PDF 摘要。

---

## 領域管理

列出領域：

```bash
PYTHONPATH=src python -m paper_report.cli profiles --store configs/research_profiles.yaml list
```

新增或更新領域：

```bash
PYTHONPATH=src python -m paper_report.cli profiles --store configs/research_profiles.yaml upsert \
  --id agent_coordination \
  --data-file configs/research_profile.yaml
```

用 JSON patch 更新欄位：

```bash
PYTHONPATH=src python -m paper_report.cli profiles --store configs/research_profiles.yaml upsert \
  --id agent_coordination \
  --json '{"description":"新的領域描述","positive_keywords":["agent coordination"]}'
```

刪除領域：

```bash
PYTHONPATH=src python -m paper_report.cli profiles --store configs/research_profiles.yaml delete --id agent_coordination
```

---

## 報告生成路線備註

### NotebookLM 路線

目前已實作：

1. 透過 `notebooklm-mcp-cli` / `nlm` 建立 NotebookLM notebook。
2. 加入論文 PDF URL 或 landing URL 作為 source。
3. 使用 Report / Briefing Doc 產生 Markdown 報告並下載。
4. 使用 Video Overview 產生影片並下載。
5. 若 NotebookLM 上傳或下載成品失敗，呼叫 OpenClaw CLI，要求 OpenClaw 以 webbridge 操作 NotebookLM 網頁補救。
6. 若 Video Overview 只是生成太久，最多等 30 分鐘後 fallback 到本地影片生成。

風險 / 備註：NotebookLM 使用非官方 internal API，需要 cookie auth。正式自動化前需在該機器跑 `nlm login` 完成 Google 登入。

### 本地報告 / 影片路線

目前已實作：

1. 以論文 metadata / abstract 產生繁體中文 Markdown 報告。
2. 報告頂部包含類別、論文類型、來源、發表年份、作者、連結、PDF 欄位。
3. 用 `ffmpeg` 產生 `.mp4` 影片；可選 `--enable-tts` 以 `edge-tts` 嘗試繁中旁白。
4. 依 `paper_type` 產生不同影片腳本：review paper 10 段，一般 paper 12 段。
5. 產生 `script.txt` 方便後續替換成更精緻的 slide / subtitle pipeline。

待補強：PDF 全文解析、LaTeX 報告、字幕、多頁 slide、Manim / slide renderer。

### YouTube / GitHub 發布與完整串接

1. 先在清理前記錄 selected papers 的 references：

```bash
PYTHONPATH=src python -m paper_report.cli record-references \
  --input outputs/daily_report.json \
  --output-dir outputs/references/$(date +%F)
```

2. 使用 OpenClaw CLI + webbridge 上傳影片到 YouTube；上傳前會要求 OpenClaw 先用 image2.0 生成適合該論文的封面圖，存成影片同資料夾的 `youtube_thumbnail.png`，並在 YouTube Studio 上傳時設定為 custom thumbnail。成功後會回寫 `manifest.json` 與 Markdown 的影片連結 / 封面路徑：

```bash
PYTHONPATH=src python -m paper_report.cli upload-videos \
  --manifest outputs/generated_reports/manifest.json \
  --privacy-status unlisted \
  --max-workers 2
```

3. 發布 Markdown 到 `openclaw572/edge-ai-papers`：

```bash
PYTHONPATH=src python -m paper_report.cli publish-github \
  --manifest outputs/generated_reports/manifest.json \
  --selection-json outputs/daily_report.json \
  --repo-url https://github.com/openclaw572/edge-ai-papers.git \
  --checkout-dir tmp/edge-ai-papers-publish \
  --project-dir . \
  --run-date $(date +%F) \
  --push
```

`publish-github` 會保留原 repo 的靜態網站架構（`index.html`、`css/`、`js/`、`reports/`），清掉舊的 pipeline / prompt / 任務說明與 README，改寫成只描述網站更新架構，再把本 project 複製到 `project/paper_report/`。第一次正式執行時也會依此規則修改原本 repo 內容並 push。

4. 一鍵完整串接：

```bash
PYTHONPATH=src python -m paper_report.cli run-full-pipeline \
  --project-dir . \
  --repo-url https://github.com/openclaw572/edge-ai-papers.git \
  --checkout-dir tmp/edge-ai-papers-publish \
  --push-github \
  --enable-tts
```

只有在 YouTube 上傳全部回傳 URL 且 GitHub publish 成功時，才會刪除 `outputs/generated_reports/`；reference 紀錄會保留在 `outputs/references/YYYY-MM-DD/`。刪除本地 generated artifacts 後，會再用 Codex CLI 寄 Gmail 給 `openclaw572@gmail.com`；若 pipeline 失敗，email 內容會包含失敗原因。若 Codex / Gmail 通知本身失敗，`pipeline_status.json` 與 cron 推播會包含錯誤原因。

### YouTube / GitHub 發布路線

已實作：

- YouTube：使用 OpenClaw CLI 叫 OpenClaw 以 webbridge 操作 YouTube Studio；上傳前要求 OpenClaw 使用 image2.0 生成論文主題封面並設為 custom thumbnail；不處理 Google 密碼，遇到登入 / 2FA / 頻道確認 / 自訂縮圖不可用會回報 blocker。
- GitHub：把 Markdown 報告 push 到指定 repo，報告頂部保留類別、來源、發表年份、作者、連結等資訊，底部補影片連結。
- Codex Gmail：完整流程結束後使用 Codex CLI 寄送 Gmail 到 `openclaw572@gmail.com`，成功/失敗都會帶上執行摘要；若失敗會包含錯誤原因。
- 清理：先記錄 references，再確認 YouTube / GitHub 成功，最後只刪除 generated Markdown / video artifacts。

---

### Cron job

已建立 Hermes cron job，名稱：`paper-report-full-pipeline-every-4-days`，排程為每 4 天執行一次。Cron 會呼叫 `~/.hermes/scripts/paper_report_full_pipeline.sh`，實際執行：

```bash
cd /home/aaron/.hermes/project/paper_report
PYTHONPATH=src python scripts/run_full_pipeline.py
```

此 job 使用 `no_agent=true`，由 script 直接輸出 `outputs/pipeline_status.json` 同等內容；若 NotebookLM / OpenClaw / GitHub / Codex Gmail 認證未完成，或 YouTube 需要人工登入，job 會失敗並保留本地 artifacts，不會清理。Cron delivery 已指定到 Discord channel `1495670834579243088`，之後此 job 的執行結果會推播到該 channel。

Hermes 全域 cron script timeout 已設定為 `cron.script_timeout_seconds: 10800`（3 小時），避免完整 pipeline 因 NotebookLM 影片等待、OpenClaw YouTube 上傳、GitHub push 或 Codex Gmail 通知耗時而被 120 秒預設值中斷，同時避免 8 小時 timeout 過長。

## 測試覆蓋

目前測試包含：

- arXiv Atom parser。
- Semantic Scholar / OpenAlex / Google Scholar parser。
- 時間窗與 fallback。
- normalize / dedupe。
- ranking and selection。
- profile store 新增 / 修改 / 刪除。
- anti-keyword-stuffing domain selection regression。
- ordered candidate sources：arXiv → Semantic Scholar → OpenAlex → Google Scholar。
- 外部來源失敗時繼續下一個來源。
- 官方 rate limit constants 與 CLI 預設值。
- 報告生成分流：`floor(n / 2)` 本地，其餘 NotebookLM。
- 本地 Markdown / 影片輸出。
- NotebookLM report download error → OpenClaw webbridge fallback。
- NotebookLM video timeout → 本地影片 fallback。
- 多篇論文平行處理並輸出 manifest。
- `paper_type` 預設 review、候選 query 加 review/survey intent、每篇候選標記 review/general、quality gate / final selection 依指定類型優先。
- Review paper 與一般 paper 的本地影片腳本結構差異。
- OpenClaw YouTube 上傳：prompt 內容、image2.0 封面 / custom thumbnail 指示、YouTube URL 解析、manifest 與 Markdown 回寫。
- GitHub 發布：清理舊 pipeline / prompt / 任務說明，只保留網站架構；產生每日與全域 reports index；複製 project 並排除 outputs/cache。
- Reference 紀錄：查詢 selected papers 的 references，並在 Markdown 中標明引用來源 paper。
- Codex Gmail 通知：使用 git workdir 呼叫 Codex CLI，prompt 包含收件人與成功/失敗原因；缺少 Codex 時回報錯誤。

執行：

```bash
PYTHONPATH=src pytest -q
```
