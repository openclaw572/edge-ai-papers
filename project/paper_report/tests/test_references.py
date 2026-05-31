from __future__ import annotations

import json

from paper_report.references import fetch_references_for_paper, record_references


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "data": [
                {
                    "contexts": ["This system builds on shared workspaces."],
                    "intents": ["background"],
                    "isInfluential": True,
                    "citedPaper": {
                        "paperId": "ref123",
                        "title": "Shared Workspace Agents",
                        "authors": [{"name": "Alice"}],
                        "year": 2025,
                        "url": "https://example.org/ref",
                        "externalIds": {"DOI": "10.123/ref"},
                    },
                }
            ]
        }


class FakeSession:
    def __init__(self):
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return FakeResponse()


def test_fetch_references_for_paper_records_which_paper_cited_reference():
    from paper_report.models import Paper

    session = FakeSession()
    result = fetch_references_for_paper(Paper(title="Citing Paper", semantic_scholar_id="abc"), session=session, sleep_seconds=0)

    assert result.citing_paper_title == "Citing Paper"
    assert result.references[0].title == "Shared Workspace Agents"
    assert result.references[0].contexts[0].startswith("This system")


def test_record_references_writes_json_and_markdown(tmp_path):
    selection = tmp_path / "daily_report.json"
    selection.write_text(
        json.dumps(
            {
                "selected_papers": [
                    {
                        "paper": {"title": "Citing Paper", "semantic_scholar_id": "abc"},
                        "semantic_relevance": 0.9,
                        "recency_score": 1,
                        "full_text_score": 1,
                        "citation_signal": 0,
                        "code_or_project_signal": 0,
                        "final_score": 0.8,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    session = FakeSession()

    json_path, md_path = record_references(selection, tmp_path / "refs", session=session, sleep_seconds=0)

    assert json_path.exists()
    assert md_path.exists()
    md = md_path.read_text(encoding="utf-8")
    assert "Citing paper: Citing Paper" in md
    assert "Shared Workspace Agents" in md
