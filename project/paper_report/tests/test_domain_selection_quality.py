from datetime import date

import pytest

from paper_report.models import Paper
from paper_report.profile import load_research_profile
from paper_report.ranking import rank_papers
from paper_report.workflow import run_with_candidates_by_window

PROFILE_PATH = "configs/research_profiles.yaml"
TODAY = date(2026, 5, 26)


def paper(title, abstract, *, citations=1, categories=None):
    return Paper(
        title=title,
        abstract=abstract,
        authors=["Fixture Author"],
        published_date="2026-04-15",
        source="fixture",
        url="https://example.org/paper",
        pdf_url="https://example.org/paper.pdf",
        open_access=True,
        citation_count=citations,
        categories=categories or ["cs.AI"],
        time_window="recent_0_to_4_months",
    )


DOMAIN_CASES = [
    (
        "agentic_ai",
        "Language-Model Planners for Tool-Mediated Long-Horizon Tasks",
        [
            paper(
                "Language-Model Planners for Tool-Mediated Long-Horizon Tasks",
                (
                    "A controller decomposes user goals into multi-step plans, calls external APIs, "
                    "stores episodic state, reflects on failed actions, and evaluates autonomous task completion."
                ),
            ),
            paper(
                "Agentic AI for Robot Swarm Traffic Control",
                (
                    "This work repeats agentic AI, AI agents, autonomous agents, and multi-agent systems, "
                    "but studies robot swarm traffic control and path planning rather than language-model task execution."
                ),
                citations=40,
            ),
            paper(
                "A Survey of Transformer Pretraining Corpora",
                "A corpus collection paper for language modeling without tool use, planning, memory, or autonomous workflows.",
                citations=50,
            ),
        ],
    ),
    (
        "edge_ai_security",
        "Confidential Neural Inference on IoT Edge Nodes under Side-Channel Threats",
        [
            paper(
                "Confidential Neural Inference on IoT Edge Nodes under Side-Channel Threats",
                (
                    "The method hardens edge-deployed models against privacy leakage, tampering, and extraction attempts "
                    "using isolated execution, encrypted parameters, and robustness checks on constrained devices."
                ),
                categories=["cs.CR"],
            ),
            paper(
                "Edge AI Security Keywords for Smart Grid Optimization",
                (
                    "This text mentions edge AI security, secure edge inference, on-device AI security, and robust edge intelligence, "
                    "but the actual contribution is smart grid optimization and wireless sensor routing."
                ),
                citations=35,
                categories=["cs.NI"],
            ),
            paper(
                "Image Classification on Mobile Accelerators",
                "A pure image classification benchmark with no privacy, adversarial, extraction, secure inference, or robustness analysis.",
                citations=60,
                categories=["cs.LG"],
            ),
        ],
    ),
    (
        "embedded_system",
        "Timing-Safe Firmware Scheduling for Low-Power Microcontroller Platforms",
        [
            paper(
                "Timing-Safe Firmware Scheduling for Low-Power Microcontroller Platforms",
                (
                    "The paper analyzes bounded-latency interrupt handling, flash-constrained firmware updates, "
                    "sensor I/O, and reliability guarantees for real-time cyber-physical deployments."
                ),
                categories=["cs.AR"],
            ),
            paper(
                "Embedded Systems Keywords for Social Media Analysis",
                (
                    "This abstract repeats embedded systems, real-time systems, firmware, microcontroller, and edge devices, "
                    "but the paper is actually about social media analysis and financial market prediction."
                ),
                citations=45,
                categories=["cs.SI"],
            ),
            paper(
                "Distributed Cloud Databases for Web Applications",
                "A pure cloud computing and web application paper without constrained devices, firmware, timing, or sensors.",
                citations=80,
                categories=["cs.DB"],
            ),
        ],
    ),
    (
        "agentic_ai_security",
        "Capability-Safe Tool Invocation for Language-Model Assistants",
        [
            paper(
                "Capability-Safe Tool Invocation for Language-Model Assistants",
                (
                    "The system confines external API calls with least-privilege capabilities, audits memory writes, "
                    "detects malicious instructions, blocks secret leakage, and evaluates autonomous assistant attack surfaces."
                ),
                categories=["cs.CR"],
            ),
            paper(
                "Agentic AI Security Keywords in Pure Cryptography",
                (
                    "This work repeats agentic AI security, LLM agent security, AI agent safety, prompt injection, "
                    "tool-use security, memory poisoning, and data exfiltration, but only studies pure cryptography primitives."
                ),
                citations=40,
                categories=["cs.CR"],
            ),
            paper(
                "Path Planning for Robot Swarms with Reinforcement Learning",
                "A robot swarm and traffic control paper about pure reinforcement learning and multi-agent path planning.",
                citations=90,
                categories=["cs.RO"],
            ),
        ],
    ),
]


@pytest.mark.parametrize("profile_id,expected_title,candidates", DOMAIN_CASES)
def test_profile_selects_semantic_domain_match_over_keyword_stuffed_decoys(profile_id, expected_title, candidates):
    profile = load_research_profile(PROFILE_PATH, profile_id=profile_id)

    ranked = rank_papers(profile, candidates, today=TODAY)
    ranked_by_title = {item.paper.title: item for item in ranked}
    expected = ranked_by_title[expected_title]
    keyword_decoy = ranked[1] if ranked[0].paper.title == expected_title else ranked[0]

    assert ranked[0].paper.title == expected_title
    assert expected.positive_keyword_score <= keyword_decoy.positive_keyword_score
    assert expected.semantic_relevance > keyword_decoy.semantic_relevance


@pytest.mark.parametrize("profile_id,expected_title,candidates", DOMAIN_CASES)
def test_workflow_selected_papers_include_the_semantic_domain_match(profile_id, expected_title, candidates):
    profile = load_research_profile(PROFILE_PATH, profile_id=profile_id)
    profile.paper_type = "any"
    # This is an evaluation fixture, so lower the minimum count; we are testing ranking behavior, not fallback volume.
    profile.quality_threshold["min_papers_required"] = 1
    profile.quality_threshold["max_papers_to_output"] = 1

    result = run_with_candidates_by_window(
        profile,
        {"recent_0_to_4_months": candidates},
        today=TODAY,
    )

    assert [item.paper.title for item in result.selected_papers] == [expected_title]
    assert result.fallback_used is False
