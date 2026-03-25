## TT-SEAL: TTD-Aware Selective Encryption for Adversarially-Robust and Low-Latency Edge AI

**來源：** arXiv (cs.CR) / Design Automation Conference 2026
**日期：** 2026 年 2 月（arXiv:2602.22238v1）
**作者：** Kyeongpil Min, Sangmin Jeon, Jae-Jin Lee, Woojoo Lee (Chung-Ang University, ETRI)
**連結：** https://arxiv.org/html/2602.22238v1

### 摘要

雲端－邊緣 AI 必須在裝置資源受限下，同時滿足模型壓縮與安全性需求。雖然 Tensor-Train Decomposition (TTD) 可縮小裝置端模型，但既有選擇性加密研究多假設權重為 dense weights，因而在 TTD 壓縮下的實用性仍不明確。我們提出 TT-SEAL，一個面向 TT-decomposed networks 的選擇性加密框架。TT-SEAL 透過敏感度導向的重要性指標對 TT cores 排序，校準一次性的魯棒性門檻，並使用 value-DP optimizer 以 AES 加密最小必要的關鍵 cores。在 TTD-aware、transfer-based threat models 與 FPGA 原型化邊緣處理器上，TT-SEAL 在 ResNet-18、MobileNetV2、VGG-16 上僅加密 4.89–15.92% 參數，即可達到完整（black-box）加密的魯棒性，並將端到端延遲中 AES 解密占比降至個位數低值（例如 ResNet-18 從 58% 降至 2.76%），從而實現兼具安全與低延遲的邊緣 AI。

### 研究動機（為什麼做這份研究）

Edge AI 部署面臨兩項互相衝突的需求：
1. **模型壓縮：** TTD 可降低邊緣部署的參數量，但也會去除冗餘
2. **安全性：** 全量加密雖可保護權重，但延遲開銷高

先前選擇性加密方法假設 dense weights，套用到 TTD 壓縮模型時效果不佳。TTD 去除冗餘後，資訊集中於較少參數，若有少量未加密就可能暴露關鍵結構。研究者因此需要一種 TTD-aware 的選擇性加密方法，在維持魯棒性的同時最小化解密負擔。

### 研究內容（做了什麼）

TT-SEAL（Selective Encryption for Adversarially-Robust and Low-Latency）是首個專為 TTD 壓縮神經網路設計的選擇性加密框架。此框架：
1. 提出 core-wise importance metric，評估各 TT-core 對安全性的影響
2. 校準資料驅動的魯棒性門檻
3. 使用 value-DP（dynamic programming）找出需加密的最小 TT-cores 集合
4. 於 FPGA 原型邊緣處理器上完成驗證

### 方法論（怎麼做 - 技術細節）

**威脅模型：**
- TTD-aware 的 transfer-based adversarial attacks
- 攻擊者可查詢 oracle model 並訓練 substitute model
- 即使僅部分參數外洩，也會提升 substitute 準確率與攻擊可遷移性

**Core-wise Importance Metric (I_acc)：**
```
I_acc(G_l,k) = (1/μ_l) × sqrt(E_x[D_val][||∂L/∂G_l,k||²_F + ||∂y/∂G_l,k||²_F])
```
- 聚合每個 core 對 loss 與輸出的第一階敏感度
- μ_l 以平均 Frobenius norm 進行跨層正規化
- 透過 backward pass + Hutchinson trick 估計 Jacobian norm

**門檻校準：**
- 每個模型／資料集僅需一次校準
- 對依 I_acc 由小到大排序的 cores 前綴進行二分搜尋
- 找出使 substitute 準確率降至 A_BB + δ（δ=3%）內的最小前綴

**Value-DP 最佳化：**
- 將最小成本選擇建模為 dynamic programming 問題
- 最小化加密成本 C_enc = Σ size(G)，其中 G ∈ S
- 約束條件：A_sub(S) ≤ A_BB + δ
- 時間／空間複雜度：O(n × V̂_max)

**演算法組件：**
1. Algorithm 1：TT-cores 的 I_acc 計算
2. Algorithm 2：以 binary search 校準 I_acc_th
3. Algorithm 3：以 Value-DP 求解最小加密集合

### 圖片／圖表說明（圖片說明）

本文包含數個關鍵圖表：

**Figure 1：使用 JBDA 的 transfer-based adversarial attack**
- 藍色路徑：攻擊者以乾淨輸入查詢 oracle O(x)，訓練 substitute F(x)，並在決策邊界附近做資料擴增
- 紅色路徑：F 產生可遷移至 O 的對抗樣本 x_adv
- 展示威脅模型與攻擊流程

**Figure 2：substitute-model accuracy 與 selective encryption ratio 的關係**
- 比較 CIFAR-10 上 dense 與 TTD-compressed ResNet-18
- 藍線（dense）：約加密 50% 權重即可達到 black-box 魯棒性
- 紅線（TTD）：需超過 90% 加密仍難以匹配 black-box
- 說明為何面向 dense 的方法不適用於 TTD 模型

**Figure 3：I_acc 與 substitute-model accuracy 的關係**
- 顯示依 I_acc 由小到大加密 cores 時，substitute 準確率呈單調下降趨勢
- 於 ResNet-18、MobileNetV2、VGG-16 皆獲驗證
- 局部回升來自資訊重疊與隨機因素

*註：若要擷取這些圖表，請下載完整 PDF 或 HTML 原始內容，並儲存至 website/reports/2026-03-25/figures/*

### 結果

**加密效率：**
- ResNet-18：加密 4.89% 參數
- MobileNetV2：介於中間比例
- VGG-16：加密 15.92% 參數

**延遲改善：**
- ResNet-18：AES 解密占比由 58% 降至 2.76%
- 各模型皆達到低個位數解密開銷

**魯棒性：**
- 可達到完整（black-box）加密之魯棒性
- substitute model 準確率維持在 black-box 基準 δ=3% 內

**FPGA 驗證：**
- 於 FPGA-based edge AI processor 完成原型驗證
- 證實可在邊緣部署中實際落地

### 結論

TT-SEAL 成功解決面向 dense 的選擇性加密方法與 TTD 壓縮模型之間的根本不匹配，方法包括：
- 利用 TT-core 結構，以較低開銷達成強保護
- 僅加密 4.89–15.92% 參數即可達到 black-box 魯棒性
- 將解密延遲開銷降低至低個位數
- 使安全、低延遲邊緣 AI 推論成為可行方案

### 研究貢獻

1. **首個 TTD-tailored 選擇性加密框架：** TT-SEAL 專為 TTD 壓縮模型設計
2. **Core 級指標與最佳化：** 敏感度導向重要性指標、魯棒門檻校準、DP 最小成本選擇
3. **原型驗證：** FPGA 實作展示顯著延遲降低
4. **安全分析：** 建立 TTD-aware 威脅模型與 transfer attack 評估

### 未來工作

可延伸方向：
- 延伸至其他張量分解格式（CP、Tucker、Tensor Ring）
- 面向動態工作負載的自適應加密
- TT-SEAL 解密硬體加速器設計
- 與 federated learning 安全機制整合
- 部分加密方案的 side-channel attack 分析

### 延伸建議（可延伸建議）

1. **實作：** 將 TT-SEAL 開源為 PyTorch extension，支援 TTD layers；並整合現有模型壓縮工具（例如 torchprune、tensorly）
2. **比較研究：** 在不同 TTD ranks 與架構上，對比面向 dense 的選擇性加密方法（Zuo et al. 2021、Tian et al. 2021）
3. **資料集測試：** 於 transfer attacks 下，在邊緣視覺資料集（CIFAR-10、ImageNet、COCO）與 NLP 任務（BERT、Whisper）評估
4. **安全性延伸：** 分析部分加密造成的 side-channel 洩漏；探討 selective decryption 的 timing attacks
5. **產品方向：** 向邊緣 AI 晶片廠商（NVIDIA Jetson、Google Coral、Hailo）授權 IP；整合至 TPU/NPU 編譯器
6. **後續研究：** 延伸到動態神經網路（early exit、conditional computation）；探索同態加密在 TT-core 運算中的應用
7. **硬體最佳化：** 針對 TT-SEAL 的稀疏解密模式設計 AES 解密加速器；優化加密 core 擷取的記憶體存取
