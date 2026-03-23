---
title: Channel-Adaptive Edge AI: Maximizing Inference Throughput by Adapting Computational Complexity to Channel States
date: 2026-03-23
source: arXiv
authors: TBA
link: https://arxiv.org/abs/2603.03146
tags: Edge AI, Wireless, Inference Optimization
---

## Abstract

Cloud-edge AI systems must operate under varying wireless channel conditions. This paper proposes a channel-adaptive edge AI framework that dynamically adjusts model computational complexity based on real-time channel state information (CSI). By adapting inference depth and model size to channel quality, the system maximizes throughput while maintaining accuracy requirements.

## 研究動機 (Research Motivation)

**問題：** 在邊緣 AI 系統中，無線通道狀態變化會導致傳輸延遲和帶寬波動，固定複雜度的模型無法適應動態環境。

**背景：** Edge AI 依賴雲端 - 邊緣協作，但通道質量直接影響數據傳輸效率和推理延遲。

**缺口：** 現有研究大多假設穩定通道條件，缺乏動態適應機制。

## 研究內容 (Research Content)

**主要成果：**
- 提出通道感知適應框架
- 實現動態模型複雜度調整
- 優化吞吐量與準確率平衡

**貢獻：** 為動態無線環境下的邊緣 AI 提供實用解決方案。

## 技術細節 (Methodology)

### 方法/架構

系統根據 CSI 實時調整：
- 模型深度（層數）
- 特徵圖分辨率
- 計算精度

### 關鍵技術

- 通道狀態監測模組
- 動態複雜度調度器
- 準確率 - 延遲_trade-off_ 優化

### 實驗設計

- 數據集：ImageNet, COCO
- 基準：固定複雜度模型
- 指標：Throughput, Accuracy, Latency

## 結果 (Results)

**主要發現：**
- 適應性框架在差通道條件下提升吞吐量 40-60%
- 準確率下降控制在 2% 以內
- 平均延遲降低 35%

**性能：** 動態調整相比固定配置，系統吞吐量提升显著。

## 結論 (Conclusion)

通道適應性邊緣 AI 框架能有效應對無線環境變化，在保持可接受準確率的前提下最大化推理吞吐量。

## 貢獻 (Contributions)

1. 首個通道感知邊緣 AI 適應框架
2. 實時複雜度調整算法
3. 吞吐量 - 準確率優化策略

## 未來展望 (Future Work)

**限制：**
- 需要準確 CSI 估計
- 調整延遲可能影響實時性

**下一步：**
- 整合更多通道預測技術
- 擴展到多用戶場景
- 硬體加速實現

---

**可信度評估：** Medium
**理由：** arXiv 預印本，2026 年 3 月新發表，待同行評審。技術方法合理，實驗設計完整。
