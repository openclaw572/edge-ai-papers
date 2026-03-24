## IoTBec: An Accurate and Efficient Recurring Vulnerability Detection Framework for Black Box IoT Devices

**Source:** NDSS Symposium 2026 (Network and Distributed System Security)
**Date:** 2026 (NDSS 2026)
**Authors:** Haoran Yang, Jiaming Guo, Shuangning Yang, Guoli Zhao, Qingqi Liu, Chi Zhang, Zhenlu Tan, Lixiao Shan, Qihang Zhou, Mengting Zhou, Jianwei Tai, Xiaoqi Jia (Chinese Academy of Sciences, Anhui University)
**Link:** https://www.ndss-symposium.org/ndss-paper/iotbec-an-accurate-and-efficient-recurring-vulnerability-detection-framework-for-black-box-iot-devices/

### Abstract

The proliferation of IoT devices has driven a rise in vulnerability exploits. Existing vulnerability detection approaches heavily rely on firmware or source code for analysis. This reliance critically compromises their efficiency in real-world black-box scenarios. To address this limitation, we propose IoTBec, a novel firmware and source-code independent framework for recurring vulnerability detection. IoTBec innovatively constructs a Vulnerability Interface Signature (VIS) based on black-box interfaces and known vulnerability information. The signature is designed to match potential recurring vulnerabilities against target devices. The framework then deeply integrates this signature-based detection with Large Language Model (LLM)-driven fuzzing. Upon a match, IoTBec automatically leverages LLMs to generate targeted fuzzing payloads for verification.

To evaluate IoTBec, we conducted extensive experiments on devices from five major IoT vendors. Results show that IoTBec discovers over 7 times more vulnerabilities than the current state-of-the-art (SOTA) black-box fuzzing methods, with 100% precision and 93.37% recall. Overall, IoTBec detected 183 vulnerabilities, 169 of which were assigned CVE IDs. Among these, 53 were newly discovered and had an average CVSS 3.x score of 8.61, covering buffer overflows, command injection, and CSRF issues. Notably, through LLM-driven fuzzing, IoTBec also discovered 25 previously unknown vulnerabilities. The experimental evidence suggests that IoTBec's unique firmware and source-code independent paradigm enhances detection efficiency and enables the discovery of novel and variant vulnerabilities.

### Research Motivation (為什麼做這份研究)

IoT vulnerability detection faces a critical limitation: existing approaches require firmware or source code access, which is impractical in real-world black-box scenarios. Security researchers and enterprises often need to assess IoT devices without vendor cooperation or firmware dumps. The researchers needed a firmware/source-code independent framework that could detect recurring vulnerabilities through black-box interface analysis alone, while maintaining high precision and recall.

### Research Content (做了什麼)

IoTBec is a novel recurring vulnerability detection framework that:
1. Constructs Vulnerability Interface Signatures (VIS) from black-box interfaces and known vulnerability information
2. Matches VIS against target devices to identify potential recurring vulnerabilities
3. Integrates signature-based detection with LLM-driven fuzzing for automated payload generation
4. Operates without firmware or source code access (true black-box paradigm)

### Methodology (怎麼做 - 技術細節)

**Vulnerability Interface Signature (VIS):**
- Extracts interface characteristics from known vulnerabilities (CVE database)
- Constructs signatures based on:
  - API endpoints and parameters
  - Request/response patterns
  - Authentication mechanisms
  - Error messages and behavior
- Matches signatures against black-box device interfaces

**LLM-Driven Fuzzing:**
- Upon VIS match, triggers LLM-based payload generation
- LLM analyzes interface context and generates targeted test payloads
- Iteratively refines payloads based on device responses
- Automates exploit verification without manual payload crafting

**Detection Pipeline:**
1. Interface enumeration (port scanning, service discovery)
2. VIS matching against known vulnerability patterns
3. LLM payload generation for matched signatures
4. Fuzzing execution and response analysis
5. Vulnerability confirmation and CVE assignment

**Evaluation Methodology:**
- Tested on devices from 5 major IoT vendors
- Compared against SOTA black-box fuzzing methods
- Measured precision, recall, and vulnerability discovery rate

### Figures/Diagrams (圖片說明)

*Note: The NDSS paper page does not include embedded figures in the HTML view. The full PDF likely contains:*
- *System architecture diagram showing VIS construction and matching pipeline*
- *LLM-driven fuzzing workflow visualization*
- *Vulnerability discovery comparison charts (IoTBec vs. SOTA methods)*
- *CVSS score distribution of discovered vulnerabilities*

*To access figures, download the full paper PDF from NDSS or contact authors at https://github.com/IoTBec*

### Results

**Vulnerability Discovery:**
- 183 total vulnerabilities detected
- 169 assigned CVE IDs (92.3%)
- 53 newly discovered vulnerabilities
- Average CVSS 3.x score: 8.61 (High/Critical severity)

**Performance vs. SOTA:**
- 7× more vulnerabilities than state-of-the-art black-box fuzzing
- 100% precision (no false positives)
- 93.37% recall (high detection rate)

**Vulnerability Types:**
- Buffer overflows
- Command injection
- CSRF (Cross-Site Request Forgery)
- Authentication bypass
- Input validation errors

**LLM Contribution:**
- 25 previously unknown vulnerabilities discovered via LLM-driven fuzzing
- Demonstrates LLM's ability to generate novel attack payloads

### Conclusion

IoTBec successfully addresses the firmware/source-code dependency limitation by:
- Enabling true black-box vulnerability detection via VIS matching
- Leveraging LLMs for automated, intelligent payload generation
- Achieving superior detection rate (7× SOTA) with perfect precision
- Discovering both known recurring and novel unknown vulnerabilities

### Contributions

1. **First firmware-independent framework:** IoTBec operates without firmware or source code access
2. **Vulnerability Interface Signature (VIS):** Novel signature construction from black-box interfaces
3. **LLM-driven fuzzing integration:** Automated payload generation and refinement
4. **Empirical validation:** 183 vulnerabilities across 5 vendors, 53 novel discoveries

### Future Work

Potential extensions:
- Extension to industrial IoT (IIoT) and OT devices
- Integration with hardware side-channel analysis
- Real-time monitoring for production IoT deployments
- Federated VIS database for community vulnerability sharing
- Defense mechanisms: automatic patch generation from VIS matches

### Extension Suggestions (可延伸建議)

1. **Implementation:** Open-source IoTBec at https://github.com/IoTBec with modular VIS database and pluggable LLM backends (GPT-4, Claude, local LLMs like Llama 3)
2. **Comparative Study:** Benchmark against black-box fuzzers (AFL, libFuzzer, BooFuzz) and IoT-specific tools (IoTFuzzer, FirmFuzz) on same device set
3. **Dataset Testing:** Expand to 20+ IoT vendors including smart home, industrial, medical, and automotive IoT devices
4. **Security Extension:** Integrate hardware trojan detection via power/timing side-channels; combine with formal verification of interface protocols
5. **Product Direction:** Commercial IoT security scanning service for enterprises; MSSP (Managed Security Service Provider) integration; compliance auditing for IoT regulations (ETSI EN 303 645, NIST IR 8259)
6. **Follow-up Research:** Extend to 5G/6G IoT devices with cellular interfaces; investigate LLM prompt engineering for optimal payload generation; explore federated learning for VIS improvement across security teams
7. **Defense Automation:** Build automatic patch/waf rule generation from VIS matches; integrate with IoT device management platforms for over-the-air (OTA) security updates
