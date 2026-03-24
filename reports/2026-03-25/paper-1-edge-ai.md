## Channel-Adaptive Edge AI: Maximizing Inference Throughput by Adapting Computational Complexity to Channel States

**Source:** arXiv (cs.IT, cs.AI, cs.LG, cs.NI)
**Date:** March 3, 2026
**Authors:** Jierui Zhang, Jianhao Huang, Kaibin Huang
**Link:** https://arxiv.org/abs/2603.03146v1

### Abstract

Integrated communication and computation (IC²) has emerged as a new paradigm for enabling efficient edge inference in sixth-generation (6G) networks. However, the design of IC² technologies is hindered by the lack of a tractable theoretical framework for characterizing end-to-end (E2E) inference performance. The metric is highly complicated as it needs to account for both channel distortion and artificial intelligence (AI) model architecture and computational complexity. In this work, we address this challenge by developing a tractable analytical model for E2E inference accuracy and leveraging it to design a channel-adaptive AI algorithm that maximizes inference throughput, referred to as the edge processing rate (EPR), under latency and accuracy constraints. Specifically, we consider an edge inference system in which a server deploys a backbone model with early exit, which enables flexible computational complexity, to perform inference on data features transmitted by a mobile device. The proposed accuracy model characterizes high-dimensional feature distributions in the angular domain using a Mixture of von Mises (MvM) distribution. This leads to a desired closed-form expression for inference accuracy as a function of quantization bit-width and model traversal depth, which represents channel distortion and computational complexity, respectively. Building upon this accuracy model, we formulate and solve the EPR maximization problem under joint latency and accuracy constraints, leading to a channel-adaptive AI algorithm that achieves full IC² integration. The proposed algorithm jointly adapts transmit-side feature compression and receive-side model complexity according to channel conditions to maximize overall efficiency and inference throughput. Experimental results demonstrate its superior performance as compared with fixed-complexity counterparts.

### Research Motivation (為什麼做這份研究)

Edge AI in 6G networks faces a fundamental challenge: there is no tractable theoretical framework for characterizing end-to-end inference performance that accounts for both channel distortion and AI model complexity. Existing approaches treat communication and computation separately, leading to suboptimal efficiency. The researchers needed to develop an analytical model that could jointly optimize feature compression (transmit side) and model complexity (receive side) based on real-time channel conditions.

### Research Content (做了什麼)

The researchers developed:
1. A tractable analytical model for E2E inference accuracy using Mixture of von Mises (MvM) distribution
2. A closed-form expression for inference accuracy as a function of quantization bit-width and model traversal depth
3. A channel-adaptive AI algorithm that maximizes Edge Processing Rate (EPR) under latency and accuracy constraints
4. An early-exit backbone model enabling flexible computational complexity

### Methodology (怎麼做 - 技術細節)

**System Model:**
- Edge inference system with server deploying backbone model with early exit
- Mobile device transmits data features to server
- Channel-adaptive AI algorithm jointly adapts:
  - Transmit-side: feature compression (quantization bit-width)
  - Receive-side: model complexity (traversal depth)

**Accuracy Model:**
- Uses Mixture of von Mises (MvM) distribution to characterize high-dimensional feature distributions in angular domain
- Derives closed-form expression: accuracy = f(quantization bits, model depth)
- Quantization bit-width represents channel distortion
- Model traversal depth represents computational complexity

**Optimization:**
- Formulates EPR maximization problem under joint latency and accuracy constraints
- Solves for optimal channel-adaptive policy
- Achieves full IC² (Integrated Communication and Computation) integration

### Figures/Diagrams (圖片說明)

*Note: The arXiv abstract page does not include embedded figures. The full PDF (3,825 KB) likely contains system architecture diagrams, accuracy model visualizations, and performance comparison charts. To access figures, download the full PDF at https://arxiv.org/pdf/2603.03146.pdf*

### Results

Experimental results demonstrate:
- Superior performance compared to fixed-complexity counterparts
- Adaptive algorithm achieves higher inference throughput under same latency/accuracy constraints
- Joint optimization of communication and computation yields significant efficiency gains

### Conclusion

The channel-adaptive AI algorithm successfully addresses the lack of tractable E2E inference performance framework by:
- Providing closed-form accuracy characterization
- Enabling dynamic adaptation to channel conditions
- Achieving full IC² integration for 6G edge inference systems

### Contributions

1. First tractable analytical model for E2E inference accuracy in IC² systems
2. MvM-based feature distribution characterization in angular domain
3. Channel-adaptive AI algorithm with joint transmit/receive optimization
4. Demonstrated superiority over fixed-complexity baselines

### Future Work

Potential extensions:
- Extension to multi-user edge inference scenarios
- Integration with specific 6G waveform designs
- Hardware implementation and real-world deployment testing
- Extension to federated learning over edge networks

### Extension Suggestions (可延伸建議)

1. **Implementation:** Build a prototype system using software-defined radio (SDR) for channel simulation and early-exit neural networks (e.g., BranchNet, MSDNet) for adaptive inference
2. **Comparative Study:** Compare against baseline approaches like static quantization, fixed early-exit thresholds, and separate comm/comp optimization
3. **Dataset Testing:** Evaluate on edge vision tasks (ImageNet, COCO) and speech recognition (LibriSpeech) under varying SNR conditions
4. **Security Extension:** Investigate privacy implications of feature compression—could adaptive quantization leak channel state information?
5. **Product Direction:** Integrate into 6G base station designs for edge AI acceleration; potential partnership with telecom equipment vendors (Ericsson, Nokia, Huawei)
6. **Follow-up Research:** Extend to multi-access edge computing (MEC) scenarios with multiple edge servers and user handoff
