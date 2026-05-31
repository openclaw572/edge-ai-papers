# 論文 Markdown / LaTeX / 影片報告與發布流程實作計畫

> 這份計畫只涵蓋「找論文以外」的工作；論文搜尋與排序 MVP 已在 `src/paper_report/` 實作。

## 目標

對已選出的論文產生繁體中文文字報告與影片報告，並依使用者指定位置發布：

1. 文字報告：Markdown 為主，可附 `.tex` / LaTeX 匯出版。
2. 影片報告：支援 NotebookLM Video Overview 或本地 ffmpeg / Manim / TTS 流程。
3. 發布：影片上傳到指定 YouTube 帳號；Markdown 上傳到指定 GitHub repo。
4. 驗證：拿到 YouTube URL 與 GitHub commit / PR / raw URL 後，才刪除本地產物。

## 架構

```text
Selected Papers JSON
  ↓
PDF / full text retrieval
  ↓
Report generator
  ├─ NotebookLM route
  └─ Local route
       ├─ Markdown / LaTeX generator
       └─ Video generator（TTS + slides + ffmpeg / Manim）
  ↓
Publishers
  ├─ YouTube uploader
  └─ GitHub report uploader
  ↓
Verification + local cleanup
```

## Phase 1：報告資料模型與輸出規範

### Task 1.1：建立報告 artifact manifest

**目的：** 每篇論文都用 manifest 追蹤本地檔案、遠端 URL、清理狀態。

**建議檔案：**

- `src/paper_report/report_artifacts.py`
- `outputs/artifacts/{paper_slug}/manifest.json`

**Manifest 欄位：**

```json
{
  "paper_id": "arxiv:2512.00001",
  "title": "...",
  "category": ["cs.AI"],
  "source": "arXiv",
  "year": "2025",
  "authors": ["..."],
  "paper_url": "https://arxiv.org/abs/...",
  "pdf_url": "https://arxiv.org/pdf/...",
  "local_markdown": "outputs/reports/.../report.md",
  "local_latex": "outputs/reports/.../report.tex",
  "local_video": "outputs/videos/.../overview.mp4",
  "youtube_url": null,
  "github_url": null,
  "cleanup_status": "pending"
}
```

### Task 1.2：Markdown 報告模板

**目的：** 確保 GitHub 上每篇報告格式一致。

**報告頂部必含：**

```markdown
---
category: [cs.AI, cs.MA]
source: arXiv
published_year: 2025
authors: [Alice, Bob]
paper_url: https://...
pdf_url: https://...
youtube_url: 待上傳
---
```

**報告底部必含：**

```markdown
## 影片連結

- YouTube: https://youtube.com/watch?v=...
```

## Phase 2：NotebookLM 路線

### Task 2.1：定義 NotebookLM browser automation 邊界

NotebookLM 目前沒有穩定公開 API。實作時應使用瀏覽器自動化，但必須遵守：

- 不要求、保存或代輸入 Google 密碼。
- 若瀏覽器未登入 Google / NotebookLM，流程停止並回報「需要使用者登入」。
- 只在已授權瀏覽器 profile 中自動上傳 PDF、點選 Reports / Video Overview、等待生成與下載。

### Task 2.2：NotebookLM Markdown 報告下載器

**流程：**

1. 開啟 NotebookLM。
2. 建立 notebook 或選取既有 notebook。
3. 上傳 PDF 或貼入論文 URL。
4. 觸發 Reports 功能。
5. 下載 / 複製 Markdown 報告。
6. 正規化成專案 Markdown 模板。

### Task 2.3：NotebookLM Video Overview 下載器

**流程：**

1. 在同一 notebook 觸發 Video Overview。
2. 等待生成完成。
3. 下載影片到 `outputs/videos/{paper_slug}/notebooklm_overview.mp4`。
4. 用 `ffprobe` 驗證影片串流、解析度、音訊與長度。

## Phase 3：本地報告路線

### Task 3.1：PDF / full text 擷取

優先順序：

1. arXiv HTML / PDF URL。
2. Semantic Scholar `openAccessPdf`。
3. OpenAlex / DOI OA 版本。
4. 若是本地 PDF，使用 `pymupdf` / `pymupdf4llm` 擷取 Markdown。

### Task 3.2：繁體中文 Markdown 摘要生成

**輸入：** title、abstract、introduction、method、experiment、conclusion。

**輸出章節：**

```markdown
# 論文標題

## 基本資訊
## 一句話摘要
## 為什麼值得看
## 主要貢獻
## 方法
## 實驗與結果
## 限制
## 可以如何用在我們的系統
## 延伸閱讀 / Seed paper 建議
## 影片連結
```

### Task 3.3：LaTeX 匯出

**做法：** 從 Markdown AST 或同一份 structured summary 產生 `.tex`。

**輸出：** `outputs/reports/{paper_slug}/report.tex`，並可選擇用 `tectonic` / `latexmk` 編譯成 PDF。

### Task 3.4：本地影片報告生成

**快速 MVP：**

1. 用摘要 JSON 產生 6～8 張投影片 PNG。
2. 用 TTS 產生繁體中文旁白。
3. 用 ffmpeg 將投影片、字幕與旁白合成 MP4。
4. 用 `ffprobe` 與 `volumedetect` 驗證影片與音量。

**進階版：** 用 Manim 製作動態 diagram / architecture / method walkthrough。

## Phase 4：YouTube 發布

### Task 4.1：YouTube 上傳介面

**優先方案：** YouTube Data API；需要 OAuth scope：

```text
https://www.googleapis.com/auth/youtube.upload
```

**替代方案：** YouTube Studio browser automation；若導向 Google Sign-In，停止並請使用者登入，不處理密碼。

### Task 4.2：上傳前驗證

```bash
ffprobe -v error -print_format json -show_format -show_streams outputs/videos/.../overview.mp4
ffmpeg -hide_banner -nostats -i outputs/videos/.../overview.mp4 -map 0:a:0 -af volumedetect -f null -
```

必須確認：

- 有 video stream。
- 有 audio stream。
- duration 合理。
- 音量不是接近靜音。

### Task 4.3：回寫 YouTube URL

上傳成功後，把 YouTube URL 寫回：

- Markdown front matter 的 `youtube_url`。
- Markdown 底部「影片連結」。
- artifact manifest。

## Phase 5：GitHub 發布

### Task 5.1：Repo 設定

使用者需提供：

- GitHub repo，例如 `owner/repo`。
- 報告目錄，例如 `papers/{category}/{year}/`。
- 發布方式：直接 commit 到 branch 或開 PR。

### Task 5.2：上傳 Markdown / LaTeX

**流程：**

1. clone 或使用既有 repo checkout。
2. 寫入 `papers/{category}/{year}/{paper_slug}.md`。
3. 若有 `.tex`，寫入同目錄。
4. commit：`docs: add paper report for {paper_slug}`。
5. push branch。
6. 回報 commit URL / PR URL / raw file URL。

## Phase 6：驗證與本地清理

### Task 6.1：遠端驗證

只有在以下條件全部成立時才清理：

- YouTube 回傳 video ID / watch URL，且狀態不是失敗。
- GitHub commit / PR 已存在，可透過 URL 讀到 Markdown。
- Markdown 中已包含正確 YouTube URL。

### Task 6.2：刪除本地報告與影片

刪除範圍只限 manifest 中列出的產物：

```text
outputs/reports/{paper_slug}/
outputs/videos/{paper_slug}/
outputs/artifacts/{paper_slug}/
```

不刪除：

- `configs/`
- `src/`
- `tests/`
- 原始專案文件
- 已寫入 GitHub repo checkout 的檔案（除非使用者明確要求）

## 需要使用者之後補充的設定

1. NotebookLM 使用哪個 Google 帳號 / 已登入瀏覽器 profile。
2. YouTube 上傳帳號與預設 visibility（建議測試先 Unlisted）。
3. GitHub repo、branch、目錄規則、是否開 PR。
4. 每篇影片長度偏好、語氣、是否要配樂、是否要顯示字幕。
