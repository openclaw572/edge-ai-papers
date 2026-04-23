# Challenges in Fuzzing Embedded Devices: Silent Memory Corruptions

## Executive Summary

The rapid proliferation of networked embedded systems, often referred to as the Internet of Things (IoT), has created a vast and vulnerable attack surface spanning consumer electronics, medical devices, and Industrial Control Systems (ICS). While memory corruption vulnerabilities remain a prevalent threat to these devices, traditional security analysis techniques—specifically fuzz-testing—face significant hurdles when transitioned from desktop environments to embedded architectures.

The core challenge lies in the phenomenon of **silent memory corruptions**. Unlike desktop systems, which utilize Memory Management Units (MMUs) and sophisticated operating system protections to trigger observable crashes upon a fault, embedded devices frequently lack these mechanisms. Consequently, a successful memory corruption may not result in a crash, but rather in a "silent" faulty state where the device continues to operate incorrectly or becomes vulnerable to later exploitation. 

Research indicates that relying solely on "liveness checks" (probing a device to see if it is still responsive) is an insufficient strategy for vulnerability discovery. Instead, a combination of full or partial emulation coupled with specific runtime heuristics—such as segment tracking and heap object tracking—is required to reliably detect 100% of memory corruption events during fuzzing sessions.

---

## Classification of Embedded Systems

To analyze the efficacy of security testing, embedded devices are categorized into three distinct types based on their operating system abstraction, which largely dictates their ability to handle and report faulty states.

| Class | Description | Examples |
| :--- | :--- | :--- |
| **Type-I** | **General-purpose OS-based.** Retrospected versions of desktop OSs, typically following minimalistic approaches. | Embedded Linux (BusyBox, uClibc) |
| **Type-II** | **Embedded OS-based.** Custom operating systems for low-power devices; often lack MMU but maintain a logical separation between kernel and application. | uClinux, ZephyrOS, VxWorks |
| **Type-III** | **No OS-Abstraction.** Monolithic firmware based on a single control loop and interrupts. System and application code are compiled together. | Contiki, TinyOS, mbed OS 2 |

---

## Core Challenges in Embedded Fuzzing

Fuzzing embedded systems is significantly more complex than fuzzing desktop software due to three primary constraints:

### [C1] Fault Detection
Desktop systems provide segmentation faults, heap hardening, and sanitizers that provide immediate feedback when a program enters an unintended state. Embedded devices often lack these, making it difficult to determine when a malformed input has successfully corrupted memory. Monitoring tools are often restricted by limited I/O capabilities, necessitating "active" or "passive" probing which may not capture internal state changes.

### [C2] Performance and Scalability
Parallelization is difficult because it often requires multiple physical units, which is cost-prohibitive. Furthermore, resetting an embedded device to a "clean state" after a crash can require a full reboot, taking seconds or minutes, whereas desktop systems can use near-instantaneous virtual machine snapshots.

### [C3] Instrumentation
Modern fuzzers like American Fuzzy Lop (AFL) rely on code-coverage instrumentation to guide input generation. However, source code is rarely available for third-party firmware, and dynamic binary instrumentation tools (like Valgrind or Pin) do not support the specialized CPU architectures and OSs used in Type-II and Type-III devices.

---

## Analysis of "Silent" Behaviors

Experiments conducted on vulnerable versions of the `expat` (XML parser) and `mbed TLS` libraries across different hardware platforms revealed that memory corruptions result in varied, often invisible, outcomes.

### Observed Behaviors Following Memory Corruption:
*   **Observable Crash:** The execution stops with a visible message (Common on Desktop/Type-I).
*   **Reboot:** The device restarts, often due to a hardware watchdog (Common on Type-II/III).
*   **Hang:** The target stops responding, potentially stuck in an infinite loop.
*   **Late Crash:** The system continues for a non-negligible time before eventually crashing during a later handler (e.g., `exit()`).
*   **Malfunctioning:** The process continues but returns incorrect results or data.
*   **No Effect:** The device continues normal operation despite corrupted internal memory.

**Key Finding:** The MMU plays a critical role. In uClinux (Type-II) and monolithic (Type-III) systems, the lack of an MMU allows programs to write to NULL-address ranges or kernel memory without triggering a fault, leading to high rates of silent corruption.

---

## Fault Detection Heuristics

To compensate for the lack of hardware protections, six heuristics can be implemented within an emulation environment (such as PANDA) to detect memory corruptions at runtime:

1.  **Segment Tracking:** Mimics an MMU by verifying if memory reads/writes occur in valid, mapped locations.
2.  **Format Specifier Tracking:** Validates that format string specifiers (for functions like `printf`) reside in read-only segments to prevent exploitation.
3.  **Heap Object Tracking:** Bookkeeps the location and size of heap objects to detect out-of-bounds accesses or use-after-free errors.
4.  **Call Stack Tracking:** A shadow-stack implementation that ensures functions return to the correct callee, detecting overwrites of return addresses.
5.  **Call Frame Tracking:** Checks that contiguous memory accesses do not cross stack frames.
6.  **Stack Object Tracking:** A fine-grained check of memory accesses against individual variable sizes and positions on the stack.

---

## Important Quotes with Context

> **"What you corrupt is not what you crash."**
*   **Context:** This is the central thesis of the research. It highlights that the direct result of a memory corruption in an embedded environment is frequently not a system failure, but a silent, undetected change in state.

> **"Embedded devices often lack such mechanisms [to detect faulty states] because of their limited I/O capabilities, constrained cost, and limited computing power."**
*   **Context:** Explaining why the security features common in the desktop world (Type-0) are absent in the embedded world (Types I-III).

> **"Fuzzing against a fully emulated target is significantly faster than against the physical device... even if the firmware is emulated, the emulator often has a much higher clock speed than (low resource) embedded devices."**
*   **Context:** Highlighting the performance benefits of moving away from physical hardware during the testing phase.

> **"The liveness check alone was only able to detect the stack-based buffer overflow and format string vulnerability... All the other vulnerabilities... were not detected by the fuzzer."**
*   **Context:** This emphasizes the failure of black-box fuzzing when no internal instrumentation or heuristics are applied.

---

## Actionable Insights

### For Security Researchers and Testers
*   **Prioritize Emulation over Physical Hardware:** Full emulation, while difficult to achieve due to peripheral complexity, allows for 100% detection of memory corruptions when combined with heuristics. It also bypasses the slow reboot times of physical hardware.
*   **Avoid "Liveness Only" Monitoring:** Testing strategies that only check if a device answers a ping or a request will miss the majority of heap-based and temporal vulnerabilities. 
*   **Implement Segment and Heap Tracking First:** These two heuristics are particularly effective at catching vulnerabilities that otherwise result in "No Effect" or "Malfunctioning" states on Type-II and Type-III devices.
*   **Utilize Partial Emulation (State Forwarding):** If full hardware documentation is unavailable, use frameworks like Avatar to run the firmware in an emulator while forwarding I/O requests to the physical device. This provides the analysis benefits of an emulator even when peripherals cannot be modeled.

### For Firmware Developers
*   **Enable Hardware Protections where Available:** Even Type-III microcontrollers (like the Cortex M-3) may have optional Memory Protection Units (MPUs). Enabling these can turn silent corruptions into observable faults, aiding both development and security auditing.
*   **Consider the Impact of Minimalist Libraries:** The use of lightweight C libraries (like uClibc) often removes heap consistency checks found in `glibc`, making memory corruptions harder to detect during testing.

### 影片報告
- YouTube：https://www.youtube.com/watch?v=OO66L1pfEUI
