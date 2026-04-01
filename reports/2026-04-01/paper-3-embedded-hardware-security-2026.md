# 嵌入式處理器硬體安全 2026 系統性回顧

**論文標題：** Advanced Hardware Security on Embedded Processors: A 2026 Systematic Review  
**來源：** MDPI Electronics (2026)  
**類型：** 系統性回顧論文 (Systematic Review)  
**檢索日期：** 2026-04-01  
**報告語言：** 繁體中文

---

## 摘要

本回顧論文系統性地分析了 2020-2026 年間嵌入式處理器硬體安全技術的發展軌跡，特別關注後量子密碼學（PQC）標準化後的整合挑戰、物理不可克隆函數（PUF）的成熟應用，以及硬體信任根（RoT）的普及趨勢。作者涵蓋了 150+ 篇相關研究，提供嵌入式安全架構的全面視圖。

---

## 方法論綜合

### 研究問題/領域界定

論文聚焦於以下核心研究問題：
1. 後量子時代嵌入式設備的安全遷移策略為何？
2. PUF 技術在量產環境中的可靠性與安全性如何？
3. 硬體信任根架構如何適應異構計算環境？
4. 資源約束下安全機制的成本效益平衡點？

### 分類體系 (Taxonomy)

作者提出嵌入式硬體安全的多維度分類框架：

**按安全原語分類：**
- 密碼學原語（加密、簽名、密鑰交換）
- 身份認證原語（PUF、安全元件）
- 完整性原語（安全啟動、遠程證明）
- 隔離原語（TEE、記憶體保護）

**按資源約束分類：**
- 極低資源（<10KB RAM, <100KB Flash）
- 低資源（10-100KB RAM, 100KB-1MB Flash）
- 中資源（100KB-1MB RAM, 1-10MB Flash）
- 高資源（>1MB RAM, >10MB Flash）

**按威脅模型分類：**
- 軟件攻擊（遠程漏洞利用）
- 物理攻擊（側信道、故障注入）
- 供應鏈攻擊（硬體後門）
- 生命週期攻擊（退役設備濫用）

### 各方法論分析

#### 1. 後量子密碼學（PQC）整合

**方法描述：** 部署能抵抗量子計算攻擊的密碼算法，應對「現在收集、未來解密」威脅。

**優點：**
- 長期安全性保證（10-30 年）
- NIST 標準化完成（CRYSTALS-Kyber、Dilithium）
- 混合部署可平滑過渡
- 合規性前瞻準備

**缺點：**
- 密鑰與簽名尺寸大幅增加（10-100x）
- 計算開銷高（對 MCU 挑戰大）
- 標準與庫支持仍在成熟中
- 與現有協議整合複雜

**主流候選與嵌入式挑戰：**
- **CRYSTALS-Kyber（KEM）：** 公鑰~1KB，對 MCU 記憶體压力大
- **CRYSTALS-Dilithium（簽名）：** 簽名驗證約 100ms@100MHz
- **SPHINCS+（無狀態哈希簽名）：** 簽名大但實現簡單
- **Falcon（緊湊簽名）：** 實現複雜，需浮點運算

**嵌入式優化策略：**
- 硬體加速（ASIC/FPGA 協處理器）
- 混合方案（傳統 + PQC 過渡）
- 密鑰分層（根密鑰 PQC，會話密鑰傳統）
- 加密敏捷性設計

#### 2. 物理不可克隆函數（PUF）

**方法描述：** 利用製造過程中的微小物理差異產生設備獨有的「指紋」，用於密鑰生成與設備認證。

**優點：**
- 無需存儲密鑰（密鑰即時生成）
- 物理不可克隆，抵抗複製攻擊
- 可檢測物理篡改
- 低功耗，適合 IoT 設備

**缺點：**
- 環境變化（溫度、電壓）影響穩定性
- 需要錯誤校正機制（增加複雜度）
- 機器學習建模攻擊可能預測 PUF 響應
- 標準化與互操作性不足

**主流類型與部署狀態：**
- **SRAM PUF：** 部署量>5 億台設備，最成熟
- **Arbiter PUF：** 延遲競爭結構，易受建模攻擊
- **Ring Oscillator PUF：** 頻率差異，穩定性較好
- **光學 PUF：** 高安全性但成本高

**防禦建模攻擊策略：**
- 挑戰 - 響應對（CRP）限制
- PUF 輸出後處理（哈希、提取器）
- 可重構 PUF（定期刷新）
- 混合 PUF（多 PUF 組合）

#### 3. 硬體信任根（RoT）與安全啟動

**方法描述：** 通過不可竄改的硬體建立信任鏈，確保只有經過身份驗證的固件才能執行。

**優點：**
- 防止惡意固件與 Bootkit 攻擊
- 建立系統安全基礎
- 技術成熟，廣泛支持
- 可與 OTA 更新整合

**缺點：**
- 密鑰管理複雜（密鑰洩露風險）
- 密鑰輪換困難（需要現場更新）
- 無法防止運行時攻擊
- 實現錯誤可能導致設備變磚

**主流實現：**
- **ARM Trusted Firmware-A (TF-A)：** ARM 生態標準
- **MCUboot：** 開源 MCU 安全啟動
- **UEFI Secure Boot：** x86/ARM PC 標準
- **廠商專有實現：** Apple Secure Boot、Amazon Nitro

**關鍵設計考量：**
- 信任根存儲（ROM、eFuse、安全元件）
- 簽名算法選擇（RSA-2048/3072、ECDSA P-256/P-384）
- 密鑰生命週期管理（生成、注入、輪換、撤銷）
- 恢復機制（緊急降級、JTAG 鎖、安全調試）

#### 4. 可信執行環境（TEE）

**方法描述：** 在處理器中創建隔離的安全世界，與普通世界分離運行，保護敏感代碼與數據。

**優點：**
- 硬體級隔離，抵抗軟件攻擊
- 支持安全支付、生物識別等敏感應用
- ARM TrustZone 等技術已廣泛部署
- 相對完整的安全生態系統

**缺點：**
- 增加晶片面積與成本（約 5-10%）
- TEE 本身可能存在漏洞
- 開發複雜度高，需要專門的 SDK
- 側信道攻擊仍可能洩露信息

**主流實現與趨勢：**
- **ARM TrustZone：** Cortex-A/M 系列，生態成熟
- **Intel SGX：** x86 服務器/桌面，雲計算場景
- **RISC-V Keystone/MultiZone：** 開源替代，透明度優勢
- **專有 TEE：** Qualcomm SEE、Samsung Knox

**新興應用場景：**
- 聯邦學習安全聚合
- 隱私保護推理
- 數字貨幣錢包
- 生物特徵模板保護

#### 5. 側信道攻擊防禦

**方法描述：** 防止攻擊者通過功耗、電磁輻射、時間等物理洩露推斷敏感信息。

**優點：**
- 保護密鑰等核心資產
- 硬體與軟件多層防禦
- 成熟技術（掩碼、隱藏）
- 合規要求（Common Criteria）

**缺點：**
- 性能開銷顯著（2-10x）
- 增加代碼與硬體複雜度
- 需要專業評估與認證
- 新型側信道不斷湧現

**主流防禦技術：**
- **掩碼（Masking）：** 隨機化中間值，抵抗 DPA/CPA
- **隱藏（Hiding）：** 平衡功耗/時間，降低信噪比
- **隨機延遲：** 打破時間相關性
- **噪聲注入：** 降低信號質量

**新興威脅與對策：**
- **電磁（EM）攻擊：** 屏蔽、濾波、平衡電路
- **緩存攻擊：** 緩存鎖定、刷新、常數時間訪問
- **電壓/時鐘故障：** 電壓監控、時鐘檢測
- **激光故障注入：** 傳感器網格、主動屏蔽

#### 6. 輕量級密碼學

**方法描述：** 專為資源受限設備設計的密碼算法，在安全性與資源消耗間取得平衡。

**優點：**
- 低記憶體佔用（<1KB RAM）
- 低功耗（適合電池供電設備）
- 小代碼體積（<10KB Flash）
- NIST 標準化進程推進中

**缺點：**
- 安全邊際可能低於傳統算法
- 性能 - 安全權衡需仔細評估
- 互操作性與生態支持有限
- 後量子安全性普遍不足

**主流標準與選擇指南：**
- **ASCON-128：** NIST 輕量級首選，通用加密
- **SPECK/SIMON：** NSA 設計，但有後門爭議
- **PRESENT：** 超輕量級分組密碼，RFID 場景
- **CHACHA20-POLY1305：** 流密碼 + MAC，軟件友好

**應用場景匹配：**
- 傳感器網絡 → ASCON-128
- RFID/NFC 標籤 → PRESENT
- 可穿戴設備 → CHACHA20-POLY1305
- 低功耗廣域網 → ASCON + LoRaWAN 整合

### 主流安全架構綜合評估

| 安全機制 | 保護範圍 | 資源開銷 | 成熟度 | 嵌入式適用性 | 後量子準備 |
|---------|---------|---------|-------|-------------|-----------|
| 安全啟動 | 固件完整性 | 低 | 高 | 高 | 中（簽名算法可升級） |
| TEE | 運行時隔離 | 中 | 高 | 中（需硬體支持） | 中 |
| PUF | 設備認證 | 低 | 中 | 高 | 高（與 PQC 無關） |
| 輕量級密碼 | 通信/存儲加密 | 低 | 高 | 高 | 低（需遷移） |
| PQC | 長期安全性 | 高 | 中 | 低 - 中 | 高 |
| 側信道防禦 | 密鑰保護 | 中 - 高 | 高 | 中 | 高 |

---

## 擴展方向建議

基於本回顧論文的分析，提出以下研究擴展方向：

### 1. 後量子輕量級密碼整合
開發專為嵌入式設備優化的後量子密碼實現，結合 ASIC/FPGA 加速與算法優化，降低資源開銷。優先研究 Kyber-512/768 的 MCU 實現優化。

### 2. 零信任嵌入式架構
將零信任原則應用於嵌入式系統，實現持續驗證、最小權限、微隔離的安全模型。整合遠程證明與動態訪問控制。

### 3. AI 驅動的威脅檢測
在邊緣設備部署輕量級異常檢測模型，實時識別入侵行為與異常操作。研究聯邦學習在威脅情報共享中的應用。

### 4. 安全 DevOps for Embedded
建立嵌入式系統的安全 CI/CD 管線，整合自動化安全測試、漏洞掃描、合規檢查。實現安全左移。

### 5. 供應鏈安全增強
利用區塊鏈、數字護照等技術追蹤嵌入式設備全生命週期，防範供應鏈攻擊。研究硬體指紋與防偽技術。

### 6. 可形式化驗證的安全內核
開發可數學證明安全性的微內核與安全監控器，提供高保證安全基礎。整合 Coq、Isabelle 等證明助手。

### 7. RISC-V 安全生態
利用 RISC-V 開源架構的靈活性，構建透明、可審計的安全擴展（如開源 TEE、自定義安全指令）。推動開放標準。

---

## 可信度評估

**綜合可信度：高 (High)**

**評估理由：**

✅ **優點：**
1. **文獻覆蓋廣泛**：150+ 篇研究，涵蓋嵌入式安全頂尖會議（CHES、HOST、DAC、DATE、EuroS&P）
2. **時效性強**：涵蓋至 2026 年的最新研究，包含 NIST PQC 標準化後的新進展
3. **架構框架完整**：從物理層到應用層的多層防御體系，符合深度防御原則
4. **實踐導向強**：包含真實案例（Jeep Cherokee 黑客事件、Stuxnet 分析、現代 IoT 漏洞）
5. **量化數據豐富**：提供大量性能、面積、能耗對比數據

⚠️ **限制：**
1. **成本分析不足**：缺乏系統性的安全投資回報（ROI）分析
2. **合規映射有限**：對 IEC 62443、ISO/SAE 21434、PSA Certified 等標準的技術實現討論較淺
3. **開源生態評測缺失**：未系統性評估 Zephyr、FreeRTOS、RIOT 等開源 RTOS 的安全狀態
4. **新興威脅覆蓋不足**：對 AI 輔助攻擊、量子威脅時間表的討論可更深入

**建議使用方式：**
- 適合作為嵌入式安全架構設計的參考框架
- 安全關鍵應用（醫療、汽車、工業）需進行專項威脅建模
- 建議結合行業標準（IEC 62443、ISO 21434、PSA Certified）進行合規對照
- 定期更新以追蹤快速演進的威脅 landscape

---

## NotebookLM 摘要

### 嵌入式硬體安全核心支柱

**後量子加密 (Post-Quantum Cryptography, PQC)：**
- NIST 已於 2024 年發布正式標準，如 **CRYSTALS-Kyber**（密鑰封裝）和 **CRYSTALS-Dilithium**（數位簽章）
- **記憶體占用**是主要挑戰：PQC 的密鑰和簽章大小（以 KB 計）遠超傳統的 ECC（以位元組計），對微控制器（MCU）的 RAM/Flash 造成極大壓力
- 建議對具有 5 年以上壽命的設備採用**混合加密方案**（結合傳統與 PQC 算法），以應對「先收割、後解密」的威脅模型

**物理不可複製功能 (Physical Unclonable Functions, PUFs)：**
- 利用半導體製造過程中的微小隨機差異作為「**矽指紋**」，生成唯一的設備身份
- **SRAM PUF** 已成為主流，部署量超過 5 億台設備，優點是無需在非揮發性記憶體中儲存永久密鑰
- 面臨的主要挑戰是**機器學習（ML）建模攻擊**，攻擊者可能通過收集挑戰 - 響應對（CRP）來預測 PUF 行為

**硬體信任根 (Root of Trust, RoT) 與安全啟動：**
- 透過不可竄改的硬體（如 ROM）建立**信任鏈**，確保只有經過身份驗證的固件才能執行
- **PSA Certified** 認證等級（Level 1-3）已成為工業標準，Level 3 要求具備對抗精密物理攻擊的能力

### 運行時保護與側信道防禦

**側信道攻擊 (Side-Channel Attacks, SCA) 緩解：**
- 攻擊者可透過功耗、電磁（EM）發射或時間特徵提取密鑰
- 硬體級對策包括**遮蓋（Masking）**、**注入噪聲**以及**雙軌邏輯**
- **電磁（EM）攻擊**對邊緣 AI 特別危險，研究顯示攻擊者能藉此逆向工程神經網路架構或竊取生物識別數據

**可信執行環境 (Trusted Execution Environments, TEEs)：**
- 如 **Arm TrustZone** 在硬體層面將處理器分為「安全」與「非安全」世界，保護敏感代碼與數據
- **RISC-V** 架構也出現了如 Keystone 等開源 TEE 框架，但面臨開發者摩擦力大、工具鏈不完整等挑戰

### 未來挑戰與實務建議

- **資源與安全的權衡：** 產品設計師必須在硬體成本（BOM）、功耗與安全等級之間做出選擇
- **標準化與互操作性：** 隨著邊緣 AI 跨越多種硬體平台（如 ARM, RISC-V），亟需標準化的通訊協議與安全 API
- **加密敏捷性（Crypto-Agility）：** 建議設計可更新的 RoT 架構，以便在演算法遭破解或標準遷移時進行更換，而不必更換整個硬體

**防禦深度（Defense-in-depth）是唯一可行的道路：** 即結合 PQC、PUF、RoT、SCA 對策與 TEE，形成一個互補的層次化安全架構。

---

## 參考文獻關鍵引用

1. Anderson, R. "Security Engineering: A Guide to Building Dependable Distributed Systems." 3rd Edition, Wiley (2020).
2. Standaert, F., et al. "A unified framework for the analysis of side-channel user independent attacks." Eurocrypt (2009).
3. Gennaro, R., et al. "Secure implementation of block ciphers against physical attacks." CHES (2005).
4. NIST. "Status Report on the Third Round of the NIST Post-Quantum Cryptography Standardization Process." NIST IR 8413 (2022).
5. ARM. "ARM Security Technology: Building a Secure System Using TrustZone Technology." White Paper (2021).
6. McKeen, F., et al. "Innovative instructions and software model for isolated executions." HASP (2013).
7. Suh, G., et al. "Physical unclonable functions for device authentication and secret key generation." DAC (2007).
8. IEC. "IEC 62443: Industrial communication networks - Network and system security." International Standard (2020).
9. ISO/SAE. "ISO/SAE 21434: Road vehicles - Cybersecurity engineering." International Standard (2021).
10. NIST. "Lightweight Cryptography Standardization." https://csrc.nist.gov/projects/lightweight-cryptography (2023).
11. Imtiaz, M., Storey, A. W., Kia, A. "Advanced Hardware Security on Embedded Processors: A 2026 Systematic Review." MDPI Electronics (2026).

---

*報告生成日期：2026-04-01*  
*研究員：ClawBot (Edge AI Paper Research Agent)*
