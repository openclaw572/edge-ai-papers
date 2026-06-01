# Paper Report 專案

本專案位於 `/home/aaron/.hermes/project/paper_report`，用途是把「研究領域設定」轉成可定期執行的完整論文報告產線：

1. 依 research profile 搜尋候選論文。
2. 依時間窗、來源順序、語意相關度與品質門檻選出論文。
3. 產生繁體中文 Markdown 報告與影片報告。
4. 蒐集每篇 selected paper 的 references。
5. 上傳影片到 YouTube，發布 Markdown 到 GitHub 靜態網站 repo。
6. 成功後刪除本次執行建立的 NotebookLM notebooks 與本地中間產物。
7. 寫入 `outputs/pipeline_status.json`，並由 Hermes cron job 將結果推播。

> 維護規則：此 README 是本專案的主要重現文件與狀態紀錄。新增功能、修改篩選規則、調整 API / rate limit、修正 cron 行為或變更輸出格式後，必須同步更新 README，並在回覆中說明「已更新 README」。

最後更新：2026-05-31。

---

## 網站與發布位置

- 靜態網站 repo：<https://github.com/openclaw572/edge-ai-papers>
- 預期 GitHub Pages URL：<https://openclaw572.github.io/edge-ai-papers/>
- 目前檢查結果：GitHub API 顯示 `has_pages=false`，因此 Pages URL 目前會回 404。若要讓網頁可直接瀏覽，需要在 GitHub repo Settings → Pages 啟用 `main` branch / root 或對應發布目錄。
- 本 pipeline 會把報告發布到 repo 內的 `reports/YYYY-MM-DD/*.md`，並更新：
  - `reports/index.json`
  - `reports/YYYY-MM-DD/index.json`
  - `project/paper_report/`（同步本專案程式與 README，讓其他 agent 可重現）

---

## 目前重要修正狀態（2026-05-31）

本次針對 cron job 失敗與使用者指出的缺失，已把設計收斂成以下規則：

1. **本地方法影片長度**
   - 本地產生的影片預設最短 `9 * 60 = 540` 秒。
   - CLI 參數：`--local-video-min-duration-seconds`。
   - 程式會用 `ffmpeg` 產生 1 fps still-video，搭配靜音或 `edge-tts` 旁白；若 TTS 音訊更長，影片會延長到音訊長度以上。

2. **Markdown 報告格式**
   - 本地 fallback 報告不再是短版 MVP。
   - 已改成參考既有網站報告的格式：metadata block、NotebookLM/自動報告標記、執行摘要、核心主題分析、表格、重要引言與背景脈絡、對本專案的啟發、限制、後續閱讀、影片報告。
   - 本地報告仍會清楚標示「metadata + abstract-based」，避免假裝已完整解析 PDF。

3. **同一次 cron job 選文不得重複**
   - 候選階段仍會用 DOI → arXiv ID → Semantic Scholar ID → normalized title 合併 metadata。
   - 最終輸出前新增 title-level de-duplication：同一 run 內 normalized title 相同時，只保留排序最高的一篇。

4. **Reference 蒐集**
   - `record-references` 預設 `--limit-per-paper 0`，代表依 Semantic Scholar `/references` 分頁一路抓到沒有 `next` 為止。
   - 每篇 selected paper 會輸出：`lookup_complete`、`total_references_recorded`、reference title/authors/year/url/doi/arxiv/context。
   - 輸出檔保留在 `outputs/references/YYYY-MM-DD/`，即使成功清理本地影片與 Markdown 也不刪除 references。

5. **清理策略**
   - 完整成功條件：所有 YouTube upload 都回傳 URL，且 GitHub publish 成功。
   - 成功後會刪除：
     - 本次 manifest 裡的 NotebookLM `notebook_id` 對應 notebooks。
     - `outputs/generated_reports/`（包含本地/NotebookLM Markdown 與 video）。
     - `outputs/daily_report.md`。
     - `outputs/daily_report.json`。
   - 保留：
     - `outputs/references/YYYY-MM-DD/`。
     - `outputs/pipeline_status.json`。
   - 若 YouTube / GitHub 失敗，會保留本地 artifacts 供除錯。

6. **YouTube / OpenClaw 穩定性**
   - YouTube upload 預設改成單 worker，避免多個 worker 同時操作同一個 browser / YouTube Studio 對話框。
   - OpenClaw upload timeout 預設提高到 5400 秒。
   - `/home/aaron/.openclaw/openclaw.json` 的 `agents.defaults.timeoutSeconds` 已設定為 5400，避免 OpenClaw RPC 約 100 秒就中止。

---

## 專案目錄

```text
configs/
  research_profile.yaml        # 單一 research profile，cron 預設使用
  research_profiles.yaml       # 多 profile store，可 profiles upsert/list/delete
fixtures/
  sample_candidates.yaml       # 離線測試候選論文
scripts/
  run_full_pipeline.py         # Hermes cron 呼叫的完整 pipeline wrapper
src/paper_report/
  arxiv_client.py              # arXiv API query / Atom parser
  semantic_scholar.py          # Semantic Scholar candidate search + metadata enrichment
  openalex.py                  # OpenAlex candidate search / abstract reconstruction
  google_scholar.py            # Google Scholar via SerpAPI（未設定 key 時回空）
  source_utils.py              # candidate source order / query / date helpers
  paper_type.py                # review/general/any 分類與 query intent
  ranking.py                   # semantic relevance + metadata score
  review.py                    # deterministic heuristic reviewer placeholder
  workflow.py                  # windows、quality gate、fallback、final selection、title 去重
  report.py                    # hunt 階段 summary Markdown
  report_generation.py         # 本地/NotebookLM Markdown + video generation
  references.py                # selected papers references 蒐集與輸出
  youtube_openclaw.py          # OpenClaw webbridge YouTube upload + thumbnail + manifest patch
  github_publish.py            # 發布 Markdown 到 edge-ai-papers repo
  codex_notify.py              # Codex CLI Gmail 通知
  pipeline.py                  # hunt → generate → references → upload → publish → cleanup → email
  cli.py                       # 所有 CLI subcommands
tests/
  test_*.py                    # pytest regression tests
docs/
  report_generation_and_delivery_plan.md
  harness_pipeline_pseudo.yaml
outputs/
  pipeline_status.json         # 最近完整 pipeline 狀態
  references/YYYY-MM-DD/       # 成功/失敗都可保留的 reference 記錄
```

---

## 從零重現環境

此機器目前 Python 為 3.11；系統環境是 PEP 668，建議用 venv 或 uv，不要直接對 system Python 安裝套件。

```bash
cd /home/aaron/.hermes/project/paper_report
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
PYTHONPATH=src pytest -q
```

如果 `python -m venv` 或 `pip` 不可用，可改用 uv：

```bash
cd /home/aaron/.hermes/project/paper_report
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
PYTHONPATH=src python -m pytest -q
```

目前 `requirements.txt`：

```text
PyYAML>=6.0
requests>=2.31.0
pytest>=8.0
```

外部工具（視功能需要）：

- `ffmpeg` / `ffprobe`：本地影片與 duration 檢查。
- `edge-tts`：選用；啟用 `--enable-tts` 時才需要。
- `nlm` / `notebooklm-mcp`：NotebookLM automation。
- `openclaw` CLI：YouTube / NotebookLM webbridge fallback、Codex/Gmail 相關自動化。
- `git`：發布到 GitHub repo。

---

## Research Profile 與選文規則

### Profile 位置

Cron 預設使用：

```text
configs/research_profile.yaml
```

Profile 重要欄位：

```yaml
topic_name: "AI Agent Coordination and File-based Collaboration"
paper_type: "review"   # 預設 review；若使用者明確要求一般研究論文才改 general；any 僅供測試/除錯
description: "..."
positive_seed_papers: []
positive_keywords: []
negative_keywords: []
arxiv_categories: []
prefer_full_text: true
search_policy: {...}
quality_threshold: {...}
```

### 時間窗策略

1. 先查最近 0–4 個月。
2. 若 qualified papers 不足 `min_papers_required`，才依序 fallback：
   - 4–12 個月前
   - 13–36 個月前
   - 36–60 個月前
3. 每篇候選會標示 `time_window`，daily report 會列出 fallback 是否被使用。

### 候選來源順序

預設順序：

```text
arxiv,semantic_scholar,openalex,google_scholar
```

每個時間窗內：

```text
arXiv
  ↓ 如果 quality gate 不足
Semantic Scholar
  ↓ 如果 quality gate 不足 / API 429 / 暫時失敗
OpenAlex
  ↓ 如果 quality gate 不足
Google Scholar via SerpAPI
```

每補一個來源都會重新 normalize、dedupe、ranking 與 quality gate；足夠就停止，不會無限制抓資料。

### 去重規則

候選 metadata 合併階段：

```text
1. DOI
2. arXiv ID
3. Semantic Scholar paperId
4. normalized title
```

最終 selected papers 輸出階段：

```text
normalized title 去重；同一標題只保留分數最高的一篇。
```

### Ranking score

```text
semantic_relevance = scaled(
  0.70 * profile_similarity
+ 0.25 * seed_similarity
+ 0.05 * positive_keyword_score
- negative_keyword_penalty
)

final_score =
  0.45 * semantic_relevance
+ 0.20 * recency_score
+ 0.15 * full_text_score
+ 0.10 * citation_signal
+ 0.10 * code_or_project_signal
```

`positive_keyword_score` 權重很低，避免 keyword stuffing 的假相關論文壓過真正相關論文。

---

## 常用 CLI

### 1. 離線 demo（不打外部 API）

```bash
cd /home/aaron/.hermes/project/paper_report
PYTHONPATH=src python -m paper_report.cli hunt \
  --profile configs/research_profile.yaml \
  --sample-candidates fixtures/sample_candidates.yaml \
  --today 2026-05-26 \
  --output outputs/daily_report.md
```

輸出：

- `outputs/daily_report.md`
- `outputs/daily_report.json`

### 2. Live paper hunt

```bash
cd /home/aaron/.hermes/project/paper_report
PYTHONPATH=src python -m paper_report.cli hunt \
  --profile configs/research_profile.yaml \
  --output outputs/daily_report.md
```

可指定候選來源順序：

```bash
PYTHONPATH=src python -m paper_report.cli hunt \
  --profile configs/research_profile.yaml \
  --candidate-sources arxiv,semantic_scholar,openalex \
  --output outputs/daily_report.md
```

### 3. 生成 Markdown / video

```bash
PYTHONPATH=src python -m paper_report.cli generate-reports \
  --input outputs/daily_report.json \
  --output-dir outputs/generated_reports \
  --max-workers 4 \
  --local-video-min-duration-seconds 540
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
  local/<paper>/script.txt
  local/<paper>/video.mp4
  notebooklm/<paper>/report.md
  notebooklm/<paper>/video.mp4
  manifest.json
```

### 4. 蒐集 references

```bash
PYTHONPATH=src python -m paper_report.cli record-references \
  --input outputs/daily_report.json \
  --output-dir outputs/references/$(date +%F) \
  --limit-per-paper 0
```

`--limit-per-paper 0` 代表：依 Semantic Scholar pagination 抓到沒有 `next` 為止。輸出：

```text
outputs/references/YYYY-MM-DD/selected_paper_references.json
outputs/references/YYYY-MM-DD/selected_paper_references.md
```

### 5. 上傳影片到 YouTube

```bash
PYTHONPATH=src python -m paper_report.cli upload-videos \
  --manifest outputs/generated_reports/manifest.json \
  --privacy-status unlisted \
  --max-workers 1 \
  --timeout-seconds 5400
```

此命令會呼叫 OpenClaw webbridge 操作 YouTube Studio：

- 上傳 `manifest.json` 裡每篇 artifact 的影片。
- 先用 image2.0 產生論文主題 thumbnail。
- 將 thumbnail 設成 YouTube custom thumbnail。
- Audience 選 `not made for kids`。
- 成功後把 `youtube_url` 和 `youtube_thumbnail_path` 回寫 manifest 與 Markdown。

遇到登入、2FA、頻道選擇或自訂縮圖權限問題時，OpenClaw prompt 要求停止並回報 blocker，不要假裝成功。

### 6. 發布 Markdown 到 GitHub repo

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

發布會更新：

- `reports/YYYY-MM-DD/*.md`
- `reports/YYYY-MM-DD/index.json`
- `reports/index.json`
- `project/paper_report/`

### 7. 一鍵完整 pipeline

```bash
PYTHONPATH=src python -m paper_report.cli run-full-pipeline \
  --project-dir . \
  --profile configs/research_profile.yaml \
  --repo-url https://github.com/openclaw572/edge-ai-papers.git \
  --checkout-dir tmp/edge-ai-papers-publish \
  --push-github \
  --enable-tts
```

測試或手動乾跑時可加：

```bash
--skip-email
--no-cleanup
```

---

## NotebookLM 設定

`notebooklm-mcp-cli` / `nlm` 已安裝在 `/home/aaron/.local/bin`，Hermes MCP server `notebooklm` 已設定。正式使用前需確認 Google auth：

```bash
nlm login
nlm doctor
```

NotebookLM 產線做法：

1. `nlm notebook create <title>` 建立 notebook。
2. `nlm source add <notebook_id> --url <paper_pdf_or_url>` 加入 source。
3. `nlm report create ...` 產生 Briefing Doc。
4. `nlm video create ...` 產生 Video Overview。
5. `nlm download ...` 下載 report / video。
6. 若 NotebookLM 操作失敗，OpenClaw webbridge fallback 會嘗試在網頁上補救。
7. 完整成功後，pipeline 依 manifest 裡的 `notebook_id` 刪除本次建立的 notebook。

---

## API rate limit / pacing

### arXiv

官方文件：

- <https://info.arxiv.org/help/api/tou.html>
- <https://info.arxiv.org/help/api/user-manual.html>

本專案預設：

```text
ARXIV_REQUEST_INTERVAL_SECONDS = 3.0
```

### Semantic Scholar

官方文件：

- <https://www.semanticscholar.org/product/api>

本專案採保守設定：

```text
SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS = 1.0
```

可設定 API key：

```bash
export SEMANTIC_SCHOLAR_API_KEY="..."
# 或
export S2_API_KEY="..."
```

### OpenAlex

OpenAlex 不需要 key；建議設定 mailto：

```bash
export OPENALEX_MAILTO="you@example.com"
```

### Google Scholar

Google Scholar 沒有官方免費 JSON API；本專案只透過 SerpAPI：

```bash
export SERPAPI_API_KEY="..."
# 或
export GOOGLE_SCHOLAR_SERPAPI_KEY="..."
```

未設定 key 時，Google Scholar source 會安全回傳空候選，不讓 workflow 失敗。

---

## Cron job 設定

目前 Hermes cron job：

- Job ID：`1fd029b88f88`
- Name：`paper-report-full-pipeline-every-4-days`
- Schedule：`every 5760m`（每 4 天）
- Mode：`no_agent=true`
- Workdir：`/home/aaron/.hermes/project/paper_report`
- Script：`paper_report_full_pipeline.sh`
- Delivery：Discord channel `1495670834579243088`

Script 位置：

```text
/home/aaron/.hermes/scripts/paper_report_full_pipeline.sh
```

內容：

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/aaron/.hermes/project/paper_report
PYTHONPATH=src python scripts/run_full_pipeline.py
```

Wrapper `scripts/run_full_pipeline.py` 實際呼叫：

```bash
python -m paper_report.cli run-full-pipeline \
  --project-dir /home/aaron/.hermes/project/paper_report \
  --profile configs/research_profile.yaml \
  --repo-url https://github.com/openclaw572/edge-ai-papers.git \
  --checkout-dir tmp/edge-ai-papers-publish \
  --push-github \
  --enable-tts
```

可用環境變數覆寫：

- `PAPER_REPORT_RUN_DATE`
- `PAPER_REPORT_PROFILE_ID`
- `PAPER_REPORT_NO_CLEANUP=1`
- `PAPER_REPORT_EMAIL_RECIPIENT`
- `PAPER_REPORT_SKIP_EMAIL=1`

Hermes cron script timeout：

```yaml
cron:
  script_timeout_seconds: 10800
```

OpenClaw agent timeout：

```json
{
  "agents": {
    "defaults": {
      "timeoutSeconds": 5400
    }
  }
}
```

---

## 最近 cron 失敗根因摘要

已檢查最近兩次 cron output：

1. 2026-05-30：Hermes cron script 120 秒 timeout。之後已把 `cron.script_timeout_seconds` 調到 10800 秒。
2. 2026-05-31：第一篇 YouTube 上傳成功，但第二篇 OpenClaw 回 `Request timed out before a response was generated`，且本地影片過短、Markdown fallback 太短、cleanup 未執行。對應修正：
   - 本地影片最短 540 秒。
   - OpenClaw timeout 5400 秒。
   - YouTube upload 預設單 worker。
   - Markdown fallback 改為網站風格長版報告。
   - final selection 以 title 去重。
   - references 預設抓完整分頁。
   - 成功後刪除 NotebookLM notebooks、generated reports/videos、daily report 中間檔。

---

## 測試覆蓋

目前 regression tests 覆蓋：

- arXiv Atom parser。
- Semantic Scholar / OpenAlex / Google Scholar parser。
- API pacing constants 與 CLI 預設。
- 時間窗、fallback、ordered candidate sources。
- normalize / metadata dedupe。
- final selected papers title-level dedupe。
- semantic ranking 與 anti-keyword-stuffing。
- `paper_type` 預設 review、general/any 行為、query intent。
- 本地 Markdown 長版格式。
- 本地影片最短 8 分鐘以上。
- NotebookLM report download error → OpenClaw fallback。
- NotebookLM video timeout → 本地影片 fallback。
- 多篇論文平行生成與 manifest。
- YouTube upload prompt、image2.0 thumbnail、manifest/Markdown 回寫。
- GitHub publish、daily/global index、project copy。
- references pagination 與 Markdown/JSON 輸出。
- successful cleanup：NotebookLM notebooks、generated reports/videos、daily report 中間檔。
- Codex Gmail notification prompt 與錯誤回報。

執行：

```bash
cd /home/aaron/.hermes/project/paper_report
PYTHONPATH=src pytest -q
```

---

## Troubleshooting

### `nlm` 未登入

症狀：NotebookLM create/source/report/video 失敗。

處理：

```bash
nlm login
nlm doctor
```

### OpenClaw 上傳 timeout

確認 `/home/aaron/.openclaw/openclaw.json`：

```json
"agents": {
  "defaults": {
    "timeoutSeconds": 5400
  }
}
```

### YouTube 需要人工登入 / 2FA / custom thumbnail 權限不足

OpenClaw prompt 會要求停止並回報 blocker。這類問題不應用假 URL 或假 thumbnail path 代替。

### GitHub Pages 404

目前 GitHub API 顯示 repo `has_pages=false`。需要到 GitHub repo Settings → Pages 啟用後，`https://openclaw572.github.io/edge-ai-papers/` 才會成為實際網頁。

### 本地 artifacts 沒有被刪除

只有在 YouTube 全部成功且 GitHub publish 成功時才 cleanup。失敗時會保留 artifacts 以便除錯。成功時 `outputs/pipeline_status.json` 會列出：

- `cleanup_done`
- `cleanup_deleted_paths`
- `cleanup_errors`

### Reference 不完整

確認使用：

```bash
--limit-per-paper 0
```

並檢查 `selected_paper_references.json` 裡每篇 paper 的：

- `lookup_complete`
- `total_references_recorded`
- `error`
