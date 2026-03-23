---
title: TT-SEAL: TTD-Aware Selective Encryption for Adversarially-Robust and Low-Latency Edge AI
date: 2026-03-23
source: arXiv
authors: Kyeongpil Min, Sangmin Jeon, Jae-Jin Lee, Woojoo Lee
link: https://arxiv.org/abs/2602.22238
tags: Edge AI, Security, Encryption, TTD
---

## Abstract

Cloud-edge AI must jointly satisfy model compression and security under tight device budgets. While Tensor-Train Decomposition (TTD) shrinks on-device models, prior selective-encryption studies largely assume dense weights, leaving its practicality under TTD compression unclear. We present TT-SEAL, a selective-encryption framework for TT-decomposed networks. TT-SEAL ranks TT cores with a sensitivity-based importance metric, calibrates a one-time robustness threshold, and uses a value-DP optimizer to encrypt the minimum set of critical cores with AES. Under TTD-aware, transfer-based threat models (and on an FPGA-prototyped edge processor) TT-SEAL matches the robustness of full (black-box) encryption while encrypting as little as 4.89-15.92% of parameters across ResNet-18, MobileNetV2, and VGG-16, and drives the share of AES decryption in end-to-end latency to low single digits (e.g., 58% -> 2.76% on ResNet-18), enabling secure, low-latency edge AI.

## 研究動機 (Research Motivation)

**問題：** 邊緣 AI 模型需要在資源受限設備上同時滿足模型壓縮和安全加密，但現有選擇性加密研究假設密集權重，不適用於 TTD 壓縮模型。

**背景：** Tensor-Train Decomposition (TTD) 是常見的模型壓縮技術，但加密整個壓縮模型會帶來顯著延遲開銷。

**缺口：** 缺乏針對 TTD 分解網絡的選擇性加密框架，無法平衡安全性與延遲。

## 研究內容 (Research Content)

**主要成果：**
- 提出 TT-SEAL 選擇性加密框架
- 開發敏感度重要性指標排名 TT cores
- 實現最小加密集優化（4.89-15.92% 參數）
- AES 解密延遲占比從 58% 降至 2.76%

**貢獻：** 首個 TTD 感知選擇性加密方案，在 FPGA 原型邊緣處理器上驗證。

## 技術細節 (Methodology)

### 方法/架構

TT-SEAL 流程：
1. 敏感度分析：計算每個 TT core 的重要性
2. 閾值校準：一次性魯棒性閾值設定
3. Value-DP 優化器：選擇最小關鍵 core 集
4. AES 加密：僅加密選定 cores

### 關鍵技術

- **Sensitivity-based Importance Metric：** 量化 TT cores 對模型輸出的影響
- **One-time Robustness Threshold：** 校準安全閾值
- **Value-DP Optimizer：** 動態規劃選擇最優加密集
- **AES Encryption：** 標準加密算法應用於選定 cores

### 實驗設計

- 模型：ResNet-18, MobileNetV2, VGG-16
- 威脅模型：TTD-aware, transfer-based attacks
- 硬體：FPGA 原型邊緣處理器
- 指標：Robustness, Encryption Ratio, Latency Share

## 結果 (Results)

**主要發現：**
- 加密比例：4.89-15.92% 參數（依模型而異）
- 魯棒性：匹配完整（黑盒）加密
- 延遲優化：AES 解密占比 58% → 2.76%（ResNet-18）
- 跨模型一致性：MobileNetV2, VGG-16 表現相似

**性能：**
- ResNet-18: 加密 4.89%, 延遲占比 2.76%
- MobileNetV2: 加密 15.92%
- VGG-16: 中間範圍

## 結論 (Conclusion)

TT-SEAL 成功實現 TTD 分解網絡的選擇性加密，在保持與完整加密相同魯棒性的前提下，大幅降低加密開銷和延遲，使安全低延遲邊緣 AI 成為可能。

## 貢獻 (Contributions)

1. 首個 TTD 感知選擇性加密框架
2. 敏感度重要性指標與閾值校準方法
3. Value-DP 優化器實現最小加密集
4. FPGA 原型驗證與跨模型評估

## 未來展望 (Future Work)

**限制：**
- 需要預先敏感度分析
- 閾值校準為一次性，可能需適應動態場景
- 目前驗證限於特定模型架構

**下一步：**
- 擴展到更多壓縮技術（如 Pruning, Quantization）
- 動態閾值適應
- ASIC 硬體實現優化
- 對抗更多攻擊類型評估

---

**可信度評估：** High
**理由：** arXiv 預印本（2026 年 2 月），作者來自韓國頂尖大學，技術方法嚴謹，FPGA 原型驗證，實驗完整跨多個模型。加密比例和延遲優化數據具體可信。
