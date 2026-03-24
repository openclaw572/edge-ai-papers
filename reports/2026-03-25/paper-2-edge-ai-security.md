## TT-SEAL: TTD-Aware Selective Encryption for Adversarially-Robust and Low-Latency Edge AI

**Source:** arXiv (cs.CR) / Design Automation Conference 2026
**Date:** February 2026 (arXiv:2602.22238v1)
**Authors:** Kyeongpil Min, Sangmin Jeon, Jae-Jin Lee, Woojoo Lee (Chung-Ang University, ETRI)
**Link:** https://arxiv.org/html/2602.22238v1

### Abstract

Cloud–edge AI must jointly satisfy model compression and security under tight device budgets. While Tensor-Train Decomposition (TTD) shrinks on-device models, prior selective-encryption studies largely assume dense weights, leaving its practicality under TTD compression unclear. We present TT-SEAL, a selective-encryption framework for TT-decomposed networks. TT-SEAL ranks TT cores with a sensitivity-based importance metric, calibrates a one-time robustness threshold, and uses a value-DP optimizer to encrypt the minimum set of critical cores with AES. Under TTD-aware, transfer-based threat models—and on an FPGA-prototyped edge processor—TT-SEAL matches the robustness of full (black-box) encryption while encrypting as little as 4.89–15.92% of parameters across ResNet-18, MobileNetV2, and VGG-16, and drives the share of AES decryption in end-to-end latency to low single digits (e.g., 58% → 2.76% on ResNet-18), enabling secure, low-latency edge AI.

### Research Motivation (為什麼做這份研究)

Edge AI deployment faces two conflicting requirements:
1. **Model Compression:** TTD reduces parameter count for edge deployment but removes redundancy
2. **Security:** Full encryption protects weights but incurs high latency overhead

Prior selective encryption approaches assume dense weights and fail on TTD-compressed models. TTD removes redundancy, concentrating information into fewer parameters—leaving even small portions unencrypted exposes critical structure. The researchers needed a TTD-aware selective encryption scheme that maintains robustness while minimizing decryption overhead.

### Research Content (做了什麼)

TT-SEAL (Selective Encryption for Adversarially-Robust and Low-Latency) is the first selective encryption framework specifically designed for TTD-compressed neural networks. The framework:
1. Introduces a core-wise importance metric evaluating security impact of each TT-core
2. Calibrates a data-driven robustness threshold
3. Uses value-DP (dynamic programming) optimizer to identify minimum set of TT-cores to encrypt
4. Validates on FPGA-prototyped edge processor

### Methodology (怎麼做 - 技術細節)

**Threat Model:**
- TTD-aware transfer-based adversarial attacks
- Attacker can query oracle model and train substitute model
- Even partial parameter exposure improves substitute accuracy and attack transferability

**Core-wise Importance Metric (I_acc):**
```
I_acc(G_l,k) = (1/μ_l) × sqrt(E_x[D_val][||∂L/∂G_l,k||²_F + ||∂y/∂G_l,k||²_F])
```
- Aggregates first-order sensitivities of loss and output w.r.t. each core
- μ_l normalizes across layers using mean Frobenius norm
- Estimated via backward pass + Hutchinson trick for Jacobian norm

**Threshold Calibration:**
- One-time calibration per model/dataset
- Binary search over prefixes of cores sorted by ascending I_acc
- Finds smallest prefix reducing substitute accuracy to within A_BB + δ (δ=3%)

**Value-DP Optimization:**
- Formulates minimal-cost selection as dynamic programming problem
- Minimizes encryption cost C_enc = Σ size(G) for G ∈ S
- Subject to: A_sub(S) ≤ A_BB + δ
- Time/space complexity: O(n × V̂_max)

**Algorithm Components:**
1. Algorithm 1: I_acc computation for TT-cores
2. Algorithm 2: I_acc_th calibration via binary search
3. Algorithm 3: Value-DP for minimal encryption set

### Figures/Diagrams (圖片說明)

The paper contains several key figures:

**Figure 1: Transfer-based adversarial attack using JBDA**
- Blue path: Attacker queries oracle O(x) with clean inputs, trains substitute F(x), augments data near decision boundaries
- Red path: F generates adversarial examples x_adv that transfer to O
- Illustrates the threat model and attack procedure

**Figure 2: Substitute-model accuracy vs. selective encryption ratio**
- Compares dense vs. TTD-compressed ResNet-18 on CIFAR-10
- Blue (dense): reaches black-box robustness with ~50% encrypted weights
- Red (TTD): requires >90% encryption yet still fails to match black-box
- Demonstrates why dense-oriented selective encryption fails on TTD models

**Figure 3: Relationship between I_acc and substitute-model accuracy**
- Shows monotone decrease in substitute accuracy as cores encrypted in ascending I_acc order
- Validated across ResNet-18, MobileNetV2, VGG-16
- Occasional local rebounds due to overlapping information and stochastic factors

*Note: To capture these figures, download the full PDF or HTML source and save to website/reports/2026-03-25/figures/*

### Results

**Encryption Efficiency:**
- ResNet-18: 4.89% of parameters encrypted
- MobileNetV2: intermediate percentage
- VGG-16: 15.92% of parameters encrypted

**Latency Improvement:**
- ResNet-18: AES decryption share reduced from 58% → 2.76%
- Low single-digit decryption overhead across models

**Robustness:**
- Matches full (black-box) encryption robustness
- Substitute model accuracy within δ=3% of black-box baseline

**FPGA Validation:**
- Prototyped on FPGA-based edge AI processor
- Confirms practical feasibility for edge deployment

### Conclusion

TT-SEAL successfully addresses the fundamental mismatch between dense-oriented selective encryption and TTD-compressed models by:
- Exploiting TT-core structure for strong protection with reduced overhead
- Achieving black-box robustness while encrypting only 4.89–15.92% of parameters
- Reducing decryption latency overhead to low single digits
- Enabling secure, low-latency edge AI inference

### Contributions

1. **First TTD-tailored selective encryption:** TT-SEAL specifically designed for TTD-compressed models
2. **Core-level metric and optimization:** Sensitivity-based importance metric, robustness threshold calibration, minimal-cost selection via DP
3. **Prototype validation:** FPGA-based demonstration with significant latency reduction
4. **Security analysis:** TTD-aware threat model and transfer attack evaluation

### Future Work

Potential extensions:
- Extension to other tensor decomposition formats (CP, Tucker, Tensor Ring)
- Adaptive encryption for dynamic workloads
- Hardware accelerator design for TT-SEAL decryption
- Integration with federated learning security
- Side-channel attack analysis on partial encryption schemes

### Extension Suggestions (可延伸建議)

1. **Implementation:** Open-source TT-SEAL as PyTorch extension with TTD layer support; integrate with existing model compression toolkits (e.g., torchprune, tensorly)
2. **Comparative Study:** Benchmark against dense-oriented selective encryption (Zuo et al. 2021, Tian et al. 2021) on various TTD ranks and architectures
3. **Dataset Testing:** Evaluate on edge vision benchmarks (CIFAR-10, ImageNet, COCO) and NLP tasks (BERT, Whisper) under transfer attacks
4. **Security Extension:** Analyze side-channel leakage from partial encryption; investigate timing attacks on selective decryption
5. **Product Direction:** License IP to edge AI chip vendors (NVIDIA Jetson, Google Coral, Hailo); integrate into TPU/NPU compilers
6. **Follow-up Research:** Extend to dynamic neural networks (early exit, conditional computation); explore homomorphic encryption for encrypted TT-core operations
7. **Hardware Optimization:** Design AES decryption accelerator tailored to TT-SEAL's sparse decryption pattern; optimize memory access for encrypted core fetching
