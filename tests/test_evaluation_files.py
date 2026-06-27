from pathlib import Path
import csv


def test_ground_truth_has_minimum_questions():
    path = Path("evaluation/ground_truth.csv")
    assert path.exists()
    rows = list(csv.DictReader(path.open()))
    assert len(rows) >= 10
    assert {"id", "question", "expected_answer", "expected_sources", "category"}.issubset(rows[0].keys())


def test_questions_csv_exists():
    path = Path("evaluation/questions.csv")
    assert path.exists()
