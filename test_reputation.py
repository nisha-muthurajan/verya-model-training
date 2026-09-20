from reputation_model import compute_trust_score
from reputation_store import get_all_scores, get_raw_counts, record_outcome


def test_reputation_round_trip_and_bayesian_score(monkeypatch, tmp_path):
    monkeypatch.setenv("REPUTATION_STORE_PATH", str(tmp_path / "nested" / "reputation.json"))

    record_outcome("model-a", "backend", True)
    record_outcome("model-a", "backend", False)

    assert get_raw_counts("model-a", "backend") == (1, 1)
    assert get_all_scores()["model-a::backend"] == {"successes": 1, "failures": 1}
    score = compute_trust_score("model-a", "backend")
    assert score.trust_score == 0.5
    assert score.total_observations == 2
    assert score.confidence_level == "unproven"


def test_malformed_reputation_entries_are_ignored(monkeypatch, tmp_path):
    path = tmp_path / "reputation.json"
    path.write_text('{"valid::backend": {"successes": 2, "failures": 1}, "bad::backend": {"successes": -1, "failures": 1}}')
    monkeypatch.setenv("REPUTATION_STORE_PATH", str(path))

    assert get_raw_counts("valid", "backend") == (2, 1)
    assert get_raw_counts("bad", "backend") == (0, 0)