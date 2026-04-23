# In-Edge AI: Optimizing Mobile Edge Computing through Federated Learning

## Executive Summary
This briefing document analyzes the "In-Edge AI" framework, a novel approach to intelligentizing Mobile Edge Computing (MEC) by integrating Deep Reinforcement Learning (DRL) with Federated Learning (FL). As mobile traffic and computation demands surge, traditional backbone networks and cloud infrastructures face significant congestion and latency issues. While MEC attempts to alleviate these burdens by pushing resources to the network edge, it often lacks the intelligence required to manage highly dynamic and uncertain environments.

The proposed "In-Edge AI" framework addresses these deficiencies by utilizing collaboration between devices and edge nodes. By deploying DRL for resource optimization and FL for distributed training, the system achieves near-optimal performance in edge caching and computation offloading while drastically reducing communication overhead and preserving data privacy.

---

## Key Themes and Detailed Analysis

### 1. The Critical Need for Intelligence at the Edge
Traditional optimization methods in MEC (e.g., convex optimization and game theory) suffer from three primary limitations:
*   **Uncertain Inputs:** Key factors are often difficult to obtain due to varying wireless channels and privacy policies.
*   **Dynamic Conditions:** Integrated communication and computation systems are highly fluid, and traditional models fail to address these dynamics.
*   **Temporal Isolation:** Most algorithms optimize for a single "snapshot" of the system, ignoring the long-term effects of current resource allocation decisions.

The document defines this systemic failure as a "lack of intelligence," necessitating a shift toward cognitive, AI-driven management.

### 2. The In-Edge AI Framework
The framework partitions the edge system's cognitive process into three distinct stages:
1.  **Information Collecting:** Sensing and observing data across the MEC system, including resource usage, wireless environments, and request intensities.
2.  **Cognitive Computing:** Using observed data to perform data fusion and generate scheduling decisions.
3.  **Request Handling:** Executing the handling of user equipment (UE) requests based on intelligence-driven scheduling.

### 3. Federated Learning (FL) as an Integration Catalyst
A core contribution of this research is the use of Federated Learning to train DRL agents. This solves the "deployment challenge" where training on the cloud is too data-intensive and privacy-sensitive, and training on individual UEs is too computationally heavy.

**Core Advantages of Federated Learning in In-Edge AI:**
| Feature | Benefit to MEC System |
| :--- | :--- |
| **Non-IID Data Handling** | Manages data that is non-Independent and Identically Distributed, reflecting diverse user environments. |
| **Limited Communication** | Reduces the burden on uplink channels; only model updates (gradients) are uploaded, not raw data. |
| **Robustness** | Handles "unbalanced" data where some UEs generate significantly more tasks than others. |
| **Privacy & Security** | Raw sensitive data remains on-device; only minimal updates are shared for model aggregation. |

### 4. Use Case Applications

#### A. Edge Caching
The system addresses space-time popularity dynamics. By modeling the cache replacement problem as a Markov Decision Process (MDP), DRL agents determine whether to cache content and which local files to replace.
*   **Data Fidelity:** Simulations utilized a month-long trace from Xender (9,514 users, 188,447 files) fitted to a Zipf distribution ($\partial = 1.58$).
*   **Outcome:** The DDQN (Double Deep Q-Network) with FL achieved hit rates nearly identical to centralized models while outperforming standard FIFO, LRU, and LFU algorithms.

#### B. Computation Offloading
UEs must decide whether to execute tasks locally or offload them to an edge node via specific wireless channels while managing energy consumption.
*   **Decision Parameters:** Actions include channel selection $(c)$ and energy allocation $(e)$.
*   **Outcome:** The framework increased the utility of UEs (inversely proportional to delay, energy consumption, and task failure) to near-optimal levels compared to centralized training.

---

## Important Quotes with Context

> **"In a word, the problem existed in the resource allocation optimization of the MEC system is 'lack of intelligence'."**
*   **Context:** This statement identifies the primary motivation for the research, arguing that traditional mathematical optimization is insufficient for the 2000+ configurable parameters expected in 5G nodes.

> **"To the best of our knowledge, we are the first group to study the application of DRL coupled with Federated Learning for intelligent joint resource management of communication and computation in MEC systems."**
*   **Context:** Highlighting the novelty of the research in bridging distributed learning with edge-specific resource constraints.

> **"Server-side proxy data is less relevant than on-device data."**
*   **Context:** This justifies the shift toward Federated Learning. It argues that for the system to be truly cognitive, it must learn from the raw, real-time data experienced by the devices themselves, such as remaining battery life and local channel quality.

---

## Data-Driven Performance Evaluation

The "In-Edge AI" framework was evaluated against several baselines. The results confirm that while Federated Learning requires a "waiting period" for model merging, its long-term performance is superior in practical settings.

### Performance Comparisons
| Metric | Centralized DRL | In-Edge AI (DRL + FL) | Traditional (LRU/Greedy) |
| :--- | :--- | :--- | :--- |
| **Hit Rate (Caching)** | Highest | Near-Optimal | Low |
| **Average UE Utility** | Highest | Near-Optimal | Moderate-Low |
| **Transmission Cost** | Extremely High | **Extremely Low** | N/A |
| **Privacy Risk** | High | **Low** | Variable |

**Key Finding:** According to the source, the total wireless transmission data required to train the agent is significantly lower with FL. In caching scenarios, raw data transmission exceeds 40 MB without FL, whereas with FL, it drops to less than 2 MB.

---

## Actionable Insights

*   **Implement Transfer Learning for Deployment:** To prevent the MEC system from being "paralyzed" by random initial neural network weights, practitioners should use transfer learning. Models should be pre-trained in simulated environments before being distributed to UEs.
*   **Optimize for MLP Architectures:** The complexity of the neural network should be kept low. The study successfully used a Multi-Layer Perceptron (MLP) with a single hidden layer of 200 neurons, allowing for fast inference even on resource-constrained devices.
*   **Balance Computation and Communication:** UEs with higher energy and computation capabilities should perform more local mini-batches (local SGD updates) to further reduce the number of communication rounds required for model convergence.

---

## Challenges and Future Opportunities

1.  **URLLC Requirements:** 5G Ultra-Reliable Low-Latency Communications require millisecond responses. Current deep learning recursions may still be too slow for these specific system-level tasks.
2.  **Incentive Models:** There is a pending need for business models that reward UEs for contributing their computation power to the global model training. Blockchain is suggested as a potential integration for evaluating these contributions.
3.  **Hardware Integration:** Future development must explore the integration of FL frameworks with specialized AI chipset hardware, such as Google’s Edge TPU.
4.  **Task Splitting:** A promising research direction is the dynamic and adaptive splitting of AI tasks across multiple edge nodes and mobile devices to manage multi-dimensional resource competition.

### 影片報告
- YouTube：https://www.youtube.com/watch?v=zXOBjZF8wIA
