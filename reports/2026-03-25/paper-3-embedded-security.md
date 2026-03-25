## IoTBec: An Accurate and Efficient Recurring Vulnerability Detection Framework for Black Box IoT Devices

**來源：** NDSS Symposium 2026 (Network and Distributed System Security)
**日期：** 2026 年（NDSS 2026）
**作者：** Haoran Yang, Jiaming Guo, Shuangning Yang, Guoli Zhao, Qingqi Liu, Chi Zhang, Zhenlu Tan, Lixiao Shan, Qihang Zhou, Mengting Zhou, Jianwei Tai, Xiaoqi Jia (Chinese Academy of Sciences, Anhui University)
**連結：** https://www.ndss-symposium.org/ndss-paper/iotbec-an-accurate-and-efficient-recurring-vulnerability-detection-framework-for-black-box-iot-devices/

### 摘要

IoT 裝置快速普及，帶動漏洞利用事件增加。既有漏洞檢測方法高度依賴韌體或原始碼進行分析，這在真實黑盒場景中會嚴重限制效率。為解決此問題，我們提出 IoTBec，一個不依賴韌體與原始碼的全新 recurring vulnerability detection 框架。IoTBec 創新地基於黑盒介面與已知漏洞資訊建構 Vulnerability Interface Signature (VIS)，用於在目標裝置上比對潛在重現性漏洞。接著，框架將此簽章式檢測與 Large Language Model (LLM)-driven fuzzing 深度整合；一旦比對命中，IoTBec 便可自動利用 LLM 產生目標化 fuzzing payload 進行驗證。

為評估 IoTBec，我們在五家主要 IoT 廠商裝置上進行大量實驗。結果顯示，IoTBec 發現的漏洞數量超過現有 state-of-the-art (SOTA) black-box fuzzing 方法 7 倍以上，且達到 100% precision 與 93.37% recall。整體而言，IoTBec 共檢出 183 個漏洞，其中 169 個獲分配 CVE ID；在這些漏洞中，53 個為新發現漏洞，平均 CVSS 3.x 分數為 8.61，涵蓋緩衝區溢位、命令注入與 CSRF 等問題。值得注意的是，透過 LLM-driven fuzzing，IoTBec 另外發現 25 個先前未知漏洞。實驗證據顯示，IoTBec 的韌體／原始碼獨立範式可提升檢測效率，並有助於挖掘新型與變體漏洞。

### 研究動機（為什麼做這份研究）

IoT 漏洞檢測面臨關鍵限制：既有方法需要取得韌體或原始碼，但這在真實黑盒情境中往往不可行。資安研究人員與企業經常需要在缺乏廠商協作或韌體映像的情況下評估 IoT 裝置安全性。研究者因此需要一個不依賴韌體／原始碼的框架，能僅透過黑盒介面分析檢出重現性漏洞，同時維持高精確率與高召回率。

### 研究內容（做了什麼）

IoTBec 是一個全新的 recurring vulnerability detection 框架，具備以下能力：
1. 由黑盒介面與已知漏洞資訊建構 Vulnerability Interface Signatures (VIS)
2. 將 VIS 與目標裝置介面比對，以識別潛在重現性漏洞
3. 將簽章式檢測與 LLM-driven fuzzing 整合，自動產生測試 payload
4. 不需韌體或原始碼即可運作（真正黑盒範式）

### 方法論（怎麼做 - 技術細節）

**Vulnerability Interface Signature (VIS)：**
- 從已知漏洞（CVE 資料庫）萃取介面特徵
- 依據下列要素建構簽章：
  - API endpoints 與參數
  - 請求／回應模式
  - 驗證機制
  - 錯誤訊息與行為
- 將簽章與黑盒裝置介面進行比對

**LLM-Driven Fuzzing：**
- VIS 命中後觸發 LLM-based payload 產生
- LLM 分析介面脈絡後生成目標化測試 payload
- 依據裝置回應迭代修正 payload
- 無需人工撰寫 exploit payload 即可自動驗證

**檢測流程：**
1. 介面枚舉（port scanning、service discovery）
2. 以已知漏洞模式進行 VIS 比對
3. 對命中簽章由 LLM 產生 payload
4. 執行 fuzzing 並分析回應
5. 確認漏洞並進行 CVE 指派

**評估方法：**
- 在 5 家主要 IoT 廠商裝置上測試
- 與 SOTA black-box fuzzing 方法比較
- 衡量 precision、recall 與漏洞發現率

### 圖片／圖表說明（圖片說明）

*註：NDSS 論文頁面的 HTML 檢視未提供內嵌圖。完整 PDF 可能包含：*
- *VIS 建構與比對流程的系統架構圖*
- *LLM-driven fuzzing 工作流程視覺化*
- *漏洞發現比較圖（IoTBec vs. SOTA methods）*
- *已發現漏洞的 CVSS 分數分布*

*若要取得圖表，請自 NDSS 下載完整 PDF，或透過 https://github.com/IoTBec 聯絡作者*

### 結果

**漏洞發現：**
- 共檢出 183 個漏洞
- 169 個獲分配 CVE ID（92.3%）
- 53 個為新發現漏洞
- 平均 CVSS 3.x 分數：8.61（高／重大嚴重度）

**相較 SOTA 的效能：**
- 漏洞數量為最先進黑盒 fuzzing 方法的 7 倍
- 100% precision（零誤報）
- 93.37% recall（高檢出率）

**漏洞類型：**
- 緩衝區溢位
- 命令注入
- CSRF（Cross-Site Request Forgery）
- 認證繞過
- 輸入驗證錯誤

**LLM 貢獻：**
- 透過 LLM-driven fuzzing 發現 25 個先前未知漏洞
- 展現 LLM 生成新型攻擊 payload 的能力

### 結論

IoTBec 成功解決對韌體／原始碼依賴的限制，主要表現在：
- 透過 VIS 比對實現真正黑盒漏洞檢測
- 利用 LLM 自動化與智慧化生成 payload
- 在維持完美 precision 的同時達成 7 倍 SOTA 偵測量
- 同時發現已知重現漏洞與未知新漏洞

### 研究貢獻

1. **首個不依賴韌體的框架：** IoTBec 可在無韌體、無原始碼情境下運作
2. **Vulnerability Interface Signature (VIS)：** 自黑盒介面建構新型漏洞簽章
3. **整合 LLM-driven fuzzing：** 自動 payload 生成與迭代優化
4. **實證驗證：** 橫跨 5 家廠商共 183 個漏洞，含 53 個新發現

### 未來工作

可延伸方向：
- 延伸至工業 IoT（IIoT）與 OT 裝置
- 結合硬體 side-channel analysis
- 生產環境 IoT 的即時監測能力
- 建立社群共享的 federated VIS 資料庫
- 防禦機制：由 VIS 命中自動產生修補建議

### 延伸建議（可延伸建議）

1. **實作：** 於 https://github.com/IoTBec 開源 IoTBec，提供模組化 VIS 資料庫與可插拔 LLM 後端（GPT-4、Claude、Llama 3 等本地模型）
2. **比較研究：** 在相同裝置集合上，與 black-box fuzzers（AFL、libFuzzer、BooFuzz）及 IoT 專用工具（IoTFuzzer、FirmFuzz）比較
3. **資料集測試：** 擴展至 20+ IoT 廠商，涵蓋智慧家庭、工業、醫療與車用 IoT 裝置
4. **安全性延伸：** 整合硬體木馬偵測（power/timing side-channels）；結合介面協定形式化驗證
5. **產品方向：** 建立企業 IoT 資安掃描服務；整合 MSSP（Managed Security Service Provider）；支援 IoT 法規（ETSI EN 303 645、NIST IR 8259）合規稽核
6. **後續研究：** 延伸至具蜂巢式介面的 5G/6G IoT 裝置；研究 LLM prompt engineering 以最佳化 payload 生成；探索以 federated learning 強化 VIS
7. **防禦自動化：** 依 VIS 命中自動產生 patch/WAF 規則；與 IoT 裝置管理平台整合以支援 OTA 安全更新
