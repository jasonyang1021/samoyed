import json
from pathlib import Path


def test_ai_eval_cases_are_provider_neutral_and_evidence_aware() -> None:
    path = Path(__file__).parents[1] / "evals" / "analysis_cases.json"
    cases = json.loads(path.read_text())
    assert len(cases) >= 3
    for case in cases:
        assert case["id"]
        assert case["lab_profile"]["signal_rules"]["keywords"]
        assert case["document"]["content"]
        assert "requires_evidence_citation" in case["expected"] or "requires_uncertainty" in case["expected"]
