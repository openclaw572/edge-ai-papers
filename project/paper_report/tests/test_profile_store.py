from pathlib import Path

import yaml

from paper_report.profile import ProfileStore


def test_profile_store_add_update_delete_domain(tmp_path):
    store = ProfileStore(tmp_path / "research_profiles.yaml")

    store.add_or_update_profile(
        "agent_coordination",
        {
            "topic_name": "AI Agent Coordination",
            "description": "multi-agent workspace coordination",
            "positive_keywords": ["agent coordination"],
            "negative_keywords": ["robot swarm"],
            "arxiv_categories": ["cs.AI"],
        },
    )

    loaded = store.get_profile("agent_coordination")
    assert loaded["topic_name"] == "AI Agent Coordination"
    assert loaded["positive_keywords"] == ["agent coordination"]

    store.add_or_update_profile(
        "agent_coordination",
        {
            "description": "file-based multi-agent coordination and memory",
            "positive_keywords": ["shared workspace", "append-only log"],
        },
    )

    updated = store.get_profile("agent_coordination")
    assert updated["topic_name"] == "AI Agent Coordination"
    assert updated["description"] == "file-based multi-agent coordination and memory"
    assert updated["positive_keywords"] == ["shared workspace", "append-only log"]

    store.delete_profile("agent_coordination")
    assert store.list_profiles() == []
    saved = yaml.safe_load(Path(tmp_path / "research_profiles.yaml").read_text())
    assert saved == {"profiles": {}}
