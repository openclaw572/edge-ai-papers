from paper_report.arxiv_client import ARXIV_REQUEST_INTERVAL_SECONDS, fetch_arxiv
from paper_report.cli import build_parser
from paper_report.semantic_scholar import SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS, enrich_with_semantic_scholar, fetch_semantic_scholar


def test_official_rate_limit_constants_are_used_as_fetch_defaults():
    assert ARXIV_REQUEST_INTERVAL_SECONDS == 3.0
    assert SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS == 1.0
    assert fetch_arxiv.__defaults__[1] == ARXIV_REQUEST_INTERVAL_SECONDS
    assert fetch_semantic_scholar.__defaults__[1] == SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS
    assert enrich_with_semantic_scholar.__defaults__[0] == SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS


def test_cli_defaults_match_documented_rate_limits():
    parser = build_parser()
    args = parser.parse_args(["hunt"])

    assert args.arxiv_sleep_seconds == ARXIV_REQUEST_INTERVAL_SECONDS
    assert args.semantic_sleep_seconds == SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS
