from datetime import date

from paper_report.google_scholar import parse_serpapi_google_scholar
from paper_report.models import Window
from paper_report.openalex import parse_openalex_works
from paper_report.semantic_scholar import parse_semantic_scholar_search

WINDOW = Window("recent_0_to_4_months", start=date(2026, 1, 26), end=date(2026, 5, 26))


def test_parse_semantic_scholar_search_normalizes_search_results():
    data = {
        "data": [
            {
                "paperId": "S2-123",
                "title": "Agent Workspace Coordination",
                "abstract": "Agents coordinate through shared workspaces.",
                "publicationDate": "2026-04-10",
                "authors": [{"name": "Alice"}, {"name": "Bob"}],
                "citationCount": 7,
                "influentialCitationCount": 2,
                "isOpenAccess": True,
                "openAccessPdf": {"url": "https://example.org/paper.pdf"},
                "externalIds": {"ArXiv": "2604.00001", "DOI": "10.123/demo"},
                "url": "https://www.semanticscholar.org/paper/S2-123",
            }
        ]
    }

    papers = parse_semantic_scholar_search(data, WINDOW)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.source == "Semantic Scholar"
    assert paper.semantic_scholar_id == "S2-123"
    assert paper.arxiv_id == "2604.00001"
    assert paper.doi == "10.123/demo"
    assert paper.pdf_url == "https://example.org/paper.pdf"
    assert paper.time_window == "recent_0_to_4_months"
    assert paper.citation_count == 7
    assert paper.influential_citation_count == 2


def test_parse_openalex_works_reconstructs_abstract_and_open_access_pdf():
    data = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.123/openalex",
                "display_name": "OpenAlex Agent Memory Logs",
                "publication_date": "2026-03-01",
                "authorships": [
                    {"author": {"display_name": "Carol"}},
                    {"author": {"display_name": "Dan"}},
                ],
                "primary_location": {
                    "landing_page_url": "https://example.org/openalex",
                    "pdf_url": "https://example.org/openalex.pdf",
                },
                "open_access": {"is_oa": True, "oa_url": "https://example.org/openalex.pdf"},
                "cited_by_count": 5,
                "concepts": [{"display_name": "Artificial intelligence"}],
                "abstract_inverted_index": {"Agents": [0], "coordinate": [1], "via": [2], "logs": [3]},
            }
        ]
    }

    papers = parse_openalex_works(data, WINDOW)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.source == "OpenAlex"
    assert paper.doi == "10.123/openalex"
    assert paper.abstract == "Agents coordinate via logs"
    assert paper.authors == ["Carol", "Dan"]
    assert paper.pdf_url == "https://example.org/openalex.pdf"
    assert paper.open_access is True
    assert paper.categories == ["Artificial intelligence"]


def test_parse_serpapi_google_scholar_normalizes_pdf_resources_and_citations():
    data = {
        "organic_results": [
            {
                "title": "Google Scholar Agent Coordination",
                "snippet": "Agents coordinate with shared memory and tool logs.",
                "link": "https://example.org/google-scholar",
                "publication_info": {"summary": "Eve, Frank - 2026 - arxiv.org"},
                "inline_links": {"cited_by": {"total": 12}},
                "resources": [{"title": "PDF", "file_format": "PDF", "link": "https://example.org/google-scholar.pdf"}],
            }
        ]
    }

    papers = parse_serpapi_google_scholar(data, WINDOW)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.source == "Google Scholar"
    assert paper.title == "Google Scholar Agent Coordination"
    assert paper.abstract == "Agents coordinate with shared memory and tool logs."
    assert paper.authors == ["Eve", "Frank"]
    assert paper.published_date == "2026"
    assert paper.citation_count == 12
    assert paper.pdf_url == "https://example.org/google-scholar.pdf"
    assert paper.open_access is True
