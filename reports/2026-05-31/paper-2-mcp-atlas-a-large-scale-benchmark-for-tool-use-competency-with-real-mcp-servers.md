---
類別: Benchmark (surveying), Computer science, Task (project management), Server, Rubric, Context (archaeology), Protocol (science), Machine learning, Task analysis, Artificial intelligence, Data mining, Scheme (mathematics), Interface (matter), Software engineering, Data modeling, User interface, Flagging, Natural language, Context model
論文類型: Review paper
來源: OpenAlex
發表年份: 2026
作者: Chaithanya Bandi, Ben Hertzberg, Geobio Boo, Tejas Polakam, Jeff Da, Sami Hassaan, M. Sharma, Andrew Park, Ernesto Hernandez, Dan Rambado, Ivan Salazar, Rafael M. O. Cruz, Chetan Rane, Ben Levin, Brad Kenstler, Bing Liu, Rafael Cruz, MohammadHossein Rezaei, Chetan Rane, Ben Levin, Daniel Yue Zhang, Brad Kenstler, Bing Liu
連結: https://arxiv.org/abs/2602.00933
PDF: https://arxiv.org/pdf/2602.00933
生成方式: 本地方法
---

# MCP-Atlas: A Large-Scale Benchmark for Tool-Use Competency with Real MCP Servers

## 論文摘要

The Model Context Protocol (MCP) is emerging as a standard interface through which large language model (LLM) agents discover and invoke external tools. However, existing MCP evaluations fall short along three key axes: realistic multi-step workflows with cross-server orchestration, breadth across authentic MCP servers rather than mocks, and structured, reproducible claim-level scoring disentangled from agent verbosity or style. We introduce MCP-Atlas, a benchmark for measuring tool-use competency against production MCP servers. MCP-Atlas contains 1,000 natural-language tasks written and verified by human experts spanning 36 real MCP servers and 220 tools. Prompts do not specify servers, tools, or parameters, requiring agents to identify relevant tools among semantically plausible distractors and to compose multi-step, cross-server workflows. Each task is scored with a claim-level rubric, where final answers are scored against atomic factual claims grounded in tool outputs. This answer-centric scoring permits valid alternative tool-call trajectories to receive credit. We pair this with an 11-category diagnostic taxonomy that disentangles tool-call failures from cognitive failures in task understanding, synthesis, parsing, and stopping. Evaluating 20 frontier models from six providers under matched task-level conditions, we find pass rates up to 82.2% at a 0.75 claim coverage threshold and a clear three-tier performance structure. Automated diagnostics show that 63.3% of diagnosed failures are cognitive rather than tool-call related. Notably, several high-performing models fail after successful tool execution due to premature stopping or incorrect synthesis. We release the task schema, containerized harness, claim evaluator, and a 500-task public split, while reserving a 500-task private split to preserve leaderboard integrity. The code is at https://github.com/scaleapi/mcp-atlas.

## 為什麼值得看

此論文與目前研究領域的語意相關分數為 0.75，final score 為 0.73。若分數高，代表它同時具備主題相關性、近期性、全文可取得性與一定 metadata 訊號。

## 主要貢獻

- 探討與研究 profile 相關的核心問題。
- 提供可進一步閱讀、摘要或實作評估的方向。
- 可作為後續 NotebookLM / LLM 深度分析的輸入。

## 方法與實驗

目前 MVP 使用 metadata 與 abstract 產生初版報告；後續可串接 PDF parser 取得 introduction、method、experiment、conclusion 後補上更細的章節摘要。

## 限制

- 此報告尚未完整解析 PDF 全文。
- 方法、實驗與結論段落目前主要依 abstract / metadata 推估。

## 如何用在我們的專案

可將此論文作為領域追蹤資料，後續若與系統架構、agent workflow、工具協調、shared workspace 或安全機制相關，可加入 seed papers 或實作 backlog。

## 影片連結

待上傳。


> NotebookLM markdown 產生或下載失敗，已暫時使用本地方法補上。
