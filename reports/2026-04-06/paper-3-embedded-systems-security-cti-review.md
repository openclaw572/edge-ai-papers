## A survey of cyber threat intelligence in embedded system driven security for mobile health systems

**類別：** Embedded Systems Security（Review Paper）
**來源：** Journal of Cloud Computing (SpringerOpen)
**發表年份：** 2025/2026
**作者：** Anayo Chukwu Ikegwu, Jasmine Chifurumnanya Nnabue, Annastasia Shako Kinse, Uzoma Rita Alo
**連結：** https://journalofcloudcomputing.springeropen.com/articles/10.1186/s13677-025-00811-3

### Figures/Diagrams（圖片）
![圖 3：論文圖表截圖（SpringerOpen）](figures/p3.png)

> 圖片說明：此圖為來源文章中的實際圖表截圖（非文字敘述），用於支撐方法分類與研究脈絡。

### NotebookLM 摘要
你好，很高興能以研究專家的身份為你解析這篇關於行動健康（mHealth）系統安全的綜述論文。這篇論文詳細探討了如何利用網路威脅情資（CTI）與嵌入式系統技術來強化醫療資訊安全。

1. 論文基本資訊
- 論文標題：A survey of cyber threat intelligence in embedded system driven security for mobile health systems
- 作者：Anayo Chukwu Ikegwu 等
- 發表年份：2025（發表）/ 2026（卷期）
- 發表會議 / 期刊：Journal of Cloud Computing
- 研究領域：mHealth Security、Embedded Systems、CTI

2. 這篇 Review Paper 在整理什麼領域？
- 探討如何將 CTI 整合進 mHealth 嵌入式系統，從被動防禦轉向主動預測。

3. 為什麼重要？
- mHealth 快速擴張，資料高度敏感，設備與協議異質且資源受限。

4. Taxonomy
- mHealth 威脅與資料特性
- 嵌入式技術版圖
- CTI 分類與角色
- CTI x Embedded 整合
- 新興趨勢（AI/區塊鏈/聯邦學習）

5. 方法比較
- 傳統特徵碼：快但難防零日。
- CTI 驅動：可主動預測，但依賴情資品質與治理流程。
- 輕量加密較適配資源受限裝置。

6. 主流技術
- 可穿戴/植入式裝置安全、MFA、硬體防火牆、CTI 三層情資（戰術/行動/策略）。

7. 主要挑戰
- 算力/電力限制、即時性需求、標準化不足、更新維護困難。

8. 未來方向
- 可擴展 CTI 平台、低資源即時檢測、法規合規、跨領域協作。

9. 研究啟發
- 以 TinyML + 聯邦學習 + 區塊鏈形成隱私友善且可追溯的醫療邊緣防禦。

10. 五句摘要
- 本文回顧 CTI 在 mHealth 嵌入式安全中的角色。
- 指出隱私、完整性與可用性在醫療場景的高風險性。
- 分析資源受限設備帶來的防禦上限。
- 強調 AI/區塊鏈/聯邦學習是關鍵融合方向。
- 提出可擴展與合規落地是下一步重點。

### Review Methodology Synthesis（Review Paper）
- **問題/領域：** 嵌入式醫療裝置如何以 CTI 驅動達到主動防禦。
- **Taxonomy：** 以威脅型態、CTI 層次與嵌入式部署條件交叉分類。
- **各方法優缺點：**
  - CTI 導向偵測：預警能力強；但高度依賴外部情資整潔度。
  - 聯邦學習：資料不出域；但通訊與非 IID 問題仍明顯。
  - 區塊鏈審計：可追溯；但延遲與存儲負擔需控制。
- **主流方法：** 輕量化偵測 + 邊緣即時推論 + 雲端策略更新。
- **可延伸方向：** 發展針對醫療風險等級的自適應安全策略（risk-adaptive policy）。

### Extension Suggestions（可延伸建議）
1. 建立 mHealth CTI 資料交換格式（含匿名化與溯源欄位）。
2. 將威脅分級對應到裝置端自動防護策略（節能/強防護切換）。
3. 製作跨院區/跨廠牌的聯邦實測基準。

### Credibility Assessment（可信度評估與理由）
**評級：中高（Medium-High）**
- 優點：SpringerOpen 期刊來源、問題設定清楚、方法脈絡完整。
- 限制：領域新且場域驗證成本高，實際大規模部署證據仍待累積。