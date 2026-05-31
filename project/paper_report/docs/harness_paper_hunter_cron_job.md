# Harness Cron Job：領域相關論文自動挑選流程

## 1. 目標

建立一個由 Harness Cron Job 觸發的自動化流程，用來定期尋找特定研究領域中「較新、相關、有價值，且優先可取得全文」的論文。

本流程不以單純關鍵字搜尋為主，而是採用：

- 領域描述（Research Profile）
- Seed Papers
- Embedding Similarity
- Metadata Ranking
- Open Access / Full-text Check
- LLM Review

來判斷論文是否與目標領域相關。

---

## 2. 核心策略

### 2.1 優先搜尋最近四個月內的論文

系統每次執行時，應先搜尋「最近四個月內」的候選論文。

例如：

```text
today = 2026-05-26
primary_start_date = 2026-01-26
primary_end_date = 2026-05-26
```

第一輪只處理：

```text
published_date >= today - 4 months
```

### 2.2 如果找不到好的論文，再往四個月以前找

若最近四個月內找不到足夠好的論文，才啟動 fallback 搜尋。

Fallback 可以分成兩層：

```text
第一層 fallback：4～12 個月前
第二層 fallback：13～36 個月前
第三層 fallback：36～60 個月前（最多回溯 5 年）
```

建議不要一開始就搜尋太舊的論文，避免結果偏離「近期值得追蹤」的目標。

---

## 3. 何謂「找不到好的論文」

Harness pipeline 中需要設定品質門檻。

建議條件如下：

```yaml
quality_threshold:
  min_final_score: 0.72
  min_relevance_score: 0.75
  min_papers_required: 3
  max_papers_to_output: 5
```

判斷邏輯：

```text
如果最近四個月內 final_score >= 0.72 的論文數量 >= 3：
    使用最近四個月內的結果
否則：
    啟動 fallback，往四個月以前搜尋
```

如果 fallback 後仍不足 3 篇，則輸出目前找到的最佳結果，並在報告中標示：

```text
本次最近四個月內未找到足夠高品質論文，因此包含較舊但相關性高的論文。
```

---

## 4. Research Profile 設定檔

建議建立 `research_profile.yaml`。

範例：

```yaml
topic_name: "AI Agent Coordination and File-based Collaboration"

description: >
  Research related to AI agents, multi-agent systems, autonomous agents,
  file-based communication, shared workspace, event brokers, locking,
  append-only logs, memory stores, access control, agent coordination,
  and tool-mediated workflows.

positive_seed_papers:
  - "seed_paper_id_1"
  - "seed_paper_id_2"
  - "seed_paper_id_3"

positive_keywords:
  - "multi-agent systems"
  - "agent coordination"
  - "shared memory"
  - "tool use"
  - "file-based coordination"
  - "event broker"
  - "agent workspace"
  - "append-only log"
  - "file locking"
  - "agent memory"

negative_keywords:
  - "robot swarm"
  - "wireless sensor network"
  - "traffic control"
  - "pure reinforcement learning"
  - "multi-agent path planning"

arxiv_categories:
  - "cs.AI"
  - "cs.CL"
  - "cs.MA"
  - "cs.SE"
  - "cs.CR"

prefer_full_text: true

search_policy:
  primary_months: 4
  fallback_windows:
    - name: "fallback_4_to_12_months"
      start_months_ago: 12
      end_months_ago: 4
    - name: "fallback_13_to_36_months"
      start_months_ago: 36
      end_months_ago: 13
    - name: "fallback_36_to_60_months"
      start_months_ago: 60
      end_months_ago: 36

quality_threshold:
  min_final_score: 0.72
  min_relevance_score: 0.75
  min_papers_required: 3
  max_papers_to_output: 5
```

---

## 5. Harness Pipeline 設計

Pipeline 名稱建議：

```text
Daily Paper Hunter
```

### 5.1 Trigger

使用 Cron Trigger。

建議排程：

```text
每天早上 08:00 執行
```

或：

```text
每週一、三、五早上 08:00 執行
```

如果領域論文量很多，建議每天執行。  
如果領域較窄，建議每週 2～3 次即可。

---

## 6. Pipeline Stages

### Stage 1：Load Research Profile

目的：

- 讀取 `research_profile.yaml`
- 取得研究領域描述
- 取得 seed papers
- 取得搜尋時間範圍與品質門檻

輸出：

```json
{
  "topic_name": "...",
  "description": "...",
  "primary_date_range": {
    "start": "today - 4 months",
    "end": "today"
  },
  "fallback_windows": [...],
  "quality_threshold": {...}
}
```

---

### Stage 2：Fetch Recent Candidate Papers

目的：

先抓最近四個月內的候選論文。

資料來源建議：

- arXiv
- Semantic Scholar
- OpenAlex

第一版 MVP 可先使用：

```text
arXiv + Semantic Scholar
```

處理邏輯：

```text
1. 根據 arxiv_categories 抓最近四個月內論文
2. 根據 positive_keywords 做輔助查詢
3. 用 Semantic Scholar 補 citation、reference、openAccessPdf 等 metadata
4. 合併候選論文
```

注意：

這裡的 keyword 只用於「抓候選」，不是最後判斷依據。  
最後仍需透過 embedding similarity 與 LLM review 判斷相關性。

---

### Stage 3：Normalize and Deduplicate

目的：

將不同來源的論文資料整理成一致格式，並去除重複資料。

建議統一格式：

```json
{
  "title": "",
  "abstract": "",
  "authors": [],
  "published_date": "",
  "source": "",
  "doi": "",
  "arxiv_id": "",
  "semantic_scholar_id": "",
  "url": "",
  "pdf_url": "",
  "open_access": false,
  "citation_count": 0,
  "influential_citation_count": 0
}
```

去重邏輯優先順序：

```text
1. DOI
2. arXiv ID
3. Semantic Scholar paperId
4. title normalized string similarity
```

---

### Stage 4：Embedding Relevance Ranking

目的：

用語意相似度判斷論文是否與研究領域相關。

每篇論文的輸入文字：

```text
title + abstract
```

比較對象：

```text
1. research_profile.description
2. positive_seed_papers 的 title + abstract
```

建議計算：

```text
profile_similarity = similarity(paper, research_profile.description)
seed_similarity = max_similarity(paper, seed_papers)
semantic_relevance = 0.5 * profile_similarity + 0.5 * seed_similarity
```

如果尚未建立 seed paper embedding，可以先用 description similarity 作為 MVP。

---

### Stage 5：Full-text Availability Check

目的：

優先挑選可取得全文的論文。

檢查順序：

```text
1. arXiv PDF URL
2. Semantic Scholar openAccessPdf
3. OpenAlex open access PDF
4. DOI 對應的 open access 版本
5. 作者 project page / GitHub / lab page
```

Full-text score 建議：

```text
有可下載 PDF：1.0
有 open access landing page：0.7
只有 DOI / abstract：0.3
無法取得全文：0.0
```

---

### Stage 6：Score Papers

建議計分公式：

```text
final_score =
  0.45 * semantic_relevance
+ 0.20 * recency_score
+ 0.15 * full_text_score
+ 0.10 * citation_signal
+ 0.10 * code_or_project_signal
```

各分數說明：

| 分數 | 說明 |
|---|---|
| semantic_relevance | 與研究領域的語意相關程度 |
| recency_score | 越新的論文分數越高 |
| full_text_score | 是否可取得 PDF 或 open access 全文 |
| citation_signal | 引用數、具影響力引用數；新論文權重可降低 |
| code_or_project_signal | 是否有 GitHub、code、dataset、project page |

Recency score 建議：

```text
0～4 個月內：1.0
4～12 個月內：0.7
13～36 個月內：0.4
36～60 個月內：0.2
60 個月以上：0.2
```

---

### Stage 7：Quality Gate

目的：

判斷最近四個月內是否已找到足夠好的論文。

條件：

```text
qualified_papers =
  papers where
    final_score >= min_final_score
    and semantic_relevance >= min_relevance_score
```

判斷：

```text
if count(qualified_papers) >= min_papers_required:
    continue to LLM Review
else:
    trigger fallback search
```

範例：

```yaml
min_final_score: 0.72
min_relevance_score: 0.75
min_papers_required: 3
```

---

### Stage 8：Fallback Search

只有在最近四個月內找不到足夠好論文時才執行。

Fallback 順序：

```text
1. 搜尋 4～12 個月前
2. 若仍不足，再搜尋 13～36 個月前
3. 若仍不足，再搜尋 36～60 個月前
```

Fallback 搜尋仍然使用同樣流程：

```text
Fetch Candidates
  ↓
Normalize & Deduplicate
  ↓
Embedding Ranking
  ↓
Full-text Check
  ↓
Score Papers
  ↓
Quality Gate
```

但報告中必須標示：

```text
此論文來自 fallback window，並非最近四個月內論文。
```

---

### Stage 9：LLM Review

目的：

不要讓 LLM 處理所有候選論文，只處理排序後的 Top N。

建議：

```text
取 final_score 最高的 Top 20 給 LLM Review
```

LLM 輸入：

```json
{
  "topic_name": "...",
  "topic_description": "...",
  "paper": {
    "title": "...",
    "abstract": "...",
    "published_date": "...",
    "pdf_url": "...",
    "semantic_relevance": 0.82,
    "final_score": 0.79
  }
}
```

LLM 輸出 JSON：

```json
{
  "is_relevant": true,
  "relevance_score": 0.88,
  "novelty_score": 0.76,
  "practical_value_score": 0.81,
  "full_text_available": true,
  "reason": "This paper is relevant because it discusses coordination among autonomous agents through shared workspaces.",
  "recommended_action": "download_and_summarize_full_text"
}
```

LLM Review 重點：

- 是否真的與目標領域相關
- 是否只是關鍵字相似但主題不相關
- 是否有方法、系統、實驗或實作價值
- 是否值得下載全文並摘要
- 是否應該加入 seed paper list

---

### Stage 10：Select Final Papers

最終輸出 Top 3～5 篇。

排序建議：

```text
final_llm_score =
  0.40 * relevance_score
+ 0.25 * practical_value_score
+ 0.20 * novelty_score
+ 0.15 * full_text_available
```

輸出時分成兩類：

```text
Primary Results:
  最近四個月內找到的高品質論文

Fallback Results:
  四個月以前，但因為最近四個月內結果不足，所以補充的高相關論文
```

---

### Stage 11：Download and Summarize Full Text

對於 `recommended_action = download_and_summarize_full_text` 的論文：

```text
1. 下載 PDF
2. 擷取 title、abstract、introduction、method、experiment、conclusion
3. 產生摘要
4. 產生「為什麼值得看」
5. 產生「可不可以實作 / 跟我的系統有什麼關係」
```

摘要格式建議：

```markdown
## Paper Title

- Published Date:
- Source:
- PDF:
- Relevance:
- Why it matters:
- Main contribution:
- Method:
- Experiment:
- Limitation:
- How it can be used in our project:
```

---

### Stage 12：Notify

通知方式可選：

- Discord Webhook
- GitHub Issue
- Markdown Report
- Notion Page
- Google Drive

Discord 訊息格式建議：

```markdown
# Daily Paper Hunter Result

Topic: AI Agent Coordination and File-based Collaboration
Search Date: 2026-05-26

## Summary

- Primary window: recent 4 months
- Qualified papers found in primary window: 2
- Fallback used: Yes
- Final selected papers: 5

## Selected Papers

1. Paper Title
   - Date:
   - Score:
   - PDF:
   - Reason:

2. Paper Title
   - Date:
   - Score:
   - PDF:
   - Reason:
```

---

## 7. Harness 實作建議

### 7.1 Repository 結構

建議建立以下檔案：

```text
paper-hunter/
  configs/
    research_profile.yaml

  scripts/
    fetch_arxiv.py
    fetch_semantic_scholar.py
    fetch_openalex.py
    normalize_papers.py
    rank_papers.py
    check_full_text.py
    llm_review.py
    download_and_summarize.py
    notify_discord.py

  outputs/
    candidates.json
    ranked_papers.json
    llm_reviewed_papers.json
    final_selected_papers.json
    daily_report.md

  requirements.txt
  README.md
```

---

### 7.2 Harness Pipeline Pseudo YAML

以下是概念型 YAML，實際欄位需依你的 Harness 環境調整：

```yaml
pipeline:
  name: Daily Paper Hunter
  identifier: daily_paper_hunter
  trigger:
    type: Cron
    schedule: "0 8 * * *"

  stages:
    - stage:
        name: Load Research Profile
        type: CI
        steps:
          - run: |
              python scripts/load_profile.py                 --config configs/research_profile.yaml                 --output outputs/profile_runtime.json

    - stage:
        name: Fetch Recent Candidates
        type: CI
        steps:
          - run: |
              python scripts/fetch_arxiv.py                 --config configs/research_profile.yaml                 --months 4                 --output outputs/arxiv_recent.json

          - run: |
              python scripts/fetch_semantic_scholar.py                 --input outputs/arxiv_recent.json                 --output outputs/semantic_scholar_recent.json

    - stage:
        name: Rank Recent Papers
        type: CI
        steps:
          - run: |
              python scripts/normalize_papers.py                 --inputs outputs/arxiv_recent.json outputs/semantic_scholar_recent.json                 --output outputs/candidates_recent.json

          - run: |
              python scripts/rank_papers.py                 --config configs/research_profile.yaml                 --input outputs/candidates_recent.json                 --output outputs/ranked_recent.json

    - stage:
        name: Quality Gate
        type: CI
        steps:
          - run: |
              python scripts/quality_gate.py                 --config configs/research_profile.yaml                 --input outputs/ranked_recent.json                 --output outputs/quality_gate_result.json

    - stage:
        name: Fallback Search
        type: CI
        when:
          condition: "quality_gate_result.need_fallback == true"
        steps:
          - run: |
              python scripts/fetch_arxiv.py                 --config configs/research_profile.yaml                 --start-months-ago 12                 --end-months-ago 4                 --output outputs/arxiv_fallback_4_12.json

          - run: |
              python scripts/fetch_semantic_scholar.py                 --input outputs/arxiv_fallback_4_12.json                 --output outputs/semantic_scholar_fallback_4_12.json

          - run: |
              python scripts/normalize_papers.py                 --inputs outputs/arxiv_fallback_4_12.json outputs/semantic_scholar_fallback_4_12.json                 --output outputs/candidates_fallback_4_12.json

          - run: |
              python scripts/rank_papers.py                 --config configs/research_profile.yaml                 --input outputs/candidates_fallback_4_12.json                 --output outputs/ranked_fallback_4_12.json

    - stage:
        name: Merge and LLM Review
        type: CI
        steps:
          - run: |
              python scripts/merge_ranked_results.py                 --inputs outputs/ranked_recent.json outputs/ranked_fallback_4_12.json                 --output outputs/ranked_all.json

          - run: |
              python scripts/llm_review.py                 --config configs/research_profile.yaml                 --input outputs/ranked_all.json                 --top-n 20                 --output outputs/llm_reviewed_papers.json

    - stage:
        name: Finalize and Notify
        type: CI
        steps:
          - run: |
              python scripts/select_final_papers.py                 --input outputs/llm_reviewed_papers.json                 --max-results 5                 --output outputs/final_selected_papers.json

          - run: |
              python scripts/download_and_summarize.py                 --input outputs/final_selected_papers.json                 --output outputs/daily_report.md

          - run: |
              python scripts/notify_discord.py                 --webhook-url "$DISCORD_WEBHOOK_URL"                 --report outputs/daily_report.md
```

---

## 8. 最小可行版本 MVP

第一版建議只做以下功能：

```text
1. 讀取 research_profile.yaml
2. 搜尋最近四個月 arXiv 論文
3. 使用 Semantic Scholar 補 metadata
4. 用 embedding 算 relevance
5. 用 full-text availability 加分
6. 如果少於 3 篇好論文，依序搜尋 4～12、13～36、36～60 個月前資料
7. LLM review Top 20
8. 輸出 Top 3～5 到 Discord
```

不要第一版就做：

```text
1. 完整 citation graph
2. 自己訓練推薦模型
3. 大規模向量資料庫
4. 多來源全文爬蟲
5. 每篇 PDF 都完整解析
```

---

## 9. 建議的判斷邏輯總結

```text
Run Cron Job
  ↓
Load Research Profile
  ↓
Search recent papers within 4 months
  ↓
Rank by semantic relevance + full text + recency + value signals
  ↓
Check quality gate
  ↓
If enough good papers:
      continue
  Else:
      search older papers from 4 to 12 months ago
      rank again
      if still not enough:
          search 13 to 36 months ago
      if still not enough:
          search 36 to 60 months ago
  ↓
LLM reviews Top 20
  ↓
Select Top 3–5
  ↓
Download / summarize full text
  ↓
Send report
```

---

## 10. 給 Harness / Agent 的執行原則

Harness 或執行 agent 必須遵守：

1. **最近四個月內優先**  
   每次都先搜尋最近四個月內的論文。

2. **不要只靠關鍵字**  
   keyword 只能用來抓候選，不能作為最終選擇依據。

3. **一定要做語意相關性排序**  
   使用 research profile description 和 seed papers 進行 embedding similarity。

4. **全文可得優先**  
   有 PDF、Open Access、arXiv、Semantic Scholar openAccessPdf 的論文優先。

5. **品質不足才 fallback**  
   只有當最近四個月內找不到足夠高品質論文時，才搜尋四個月以前的資料。

6. **LLM 只審 Top N**  
   不要把所有候選論文都丟給 LLM，先排序後只審 Top 20。

7. **輸出必須說明來源時間窗**  
   每篇論文都要標示它來自：
   - recent_0_to_4_months
   - fallback_4_to_12_months
   - fallback_13_to_36_months
   - fallback_36_to_60_months

8. **報告必須透明**  
   若使用 fallback，報告必須明確說明：
   - 最近四個月找到幾篇合格論文
   - 為什麼啟動 fallback
   - fallback 後補了哪些論文

---

## 11. 最終輸出格式

每日報告建議格式：

```markdown
# Daily Paper Hunter Report

## Topic

AI Agent Coordination and File-based Collaboration

## Search Policy

- Primary window: recent 4 months
- Fallback policy: search older papers only if fewer than 3 qualified papers are found
- Fallback windows:
  - 4–12 months ago
  - 13–36 months ago
  - 36–60 months ago

## Execution Summary

- Run date:
- Candidate papers found:
- Qualified recent papers:
- Fallback used:
- Final selected papers:

## Selected Papers

### 1. Paper Title

- Published date:
- Time window:
- Source:
- PDF:
- Final score:
- LLM relevance score:
- Why selected:
- Recommended next action:

## Notes

If fallback was used, explain why.
```
