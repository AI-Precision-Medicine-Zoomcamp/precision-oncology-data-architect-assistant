"""LLM answer evaluation with a simple rubric.

This script can run in two modes:
1. heuristic mode (default): checks if answer mentions key terms from expected answer.
2. llm judge mode: set --judge and OPENAI_API_KEY to score answers with an LLM.

Usage:
    python evaluation/llm_eval.py --questions evaluation/ground_truth.csv --limit 5
    python evaluation/llm_eval.py --judge --limit 5
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from statistics import mean

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from openai import OpenAI

from src.rag.pipeline import answer_question


def keywords(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text.lower())
    stop = {"should", "using", "with", "from", "when", "where", "resource", "resources", "represented"}
    return {w for w in words if w not in stop}


def heuristic_score(answer: str, expected: str) -> dict:
    expected_kw = keywords(expected)
    answer_kw = keywords(answer)
    if not expected_kw:
        return {"score": 0.0, "reason": "No expected keywords available"}
    overlap = expected_kw & answer_kw
    score = len(overlap) / len(expected_kw)
    return {"score": round(score, 3), "reason": f"Matched {len(overlap)}/{len(expected_kw)} expected keywords", "matched_keywords": sorted(overlap)}


def judge_score(client: OpenAI, question: str, expected: str, answer: str, model: str) -> dict:
    prompt = f"""You are evaluating a RAG assistant for healthcare data modeling.
Score the answer from 0 to 5 using this rubric:
5 = correct, complete, grounded, and in scope
4 = mostly correct with minor omissions
3 = partially correct but incomplete
2 = weak or vague
1 = mostly incorrect
0 = unsafe or unrelated

Question: {question}
Expected answer: {expected}
Generated answer: {answer}

Return JSON only with keys score and reason.
"""
    response = client.responses.create(model=model, input=prompt)
    text = response.output_text.strip()
    try:
        return json.loads(text)
    except Exception:
        return {"score": None, "reason": text}


def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=Path("evaluation/ground_truth.csv"))
    parser.add_argument("--out", type=Path, default=Path("evaluation/llm_eval_results.json"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--judge-model", default=os.getenv("OPENAI_JUDGE_MODEL", "gpt-4o-mini"))
    args = parser.parse_args()

    load_dotenv()
    rows = load_rows(args.questions)
    if args.limit:
        rows = rows[: args.limit]

    client = OpenAI() if args.judge else None
    results = []
    for row in rows:
        rag = answer_question(row["question"], model=args.model)
        answer = rag["answer"]
        if args.judge and client:
            score = judge_score(client, row["question"], row["expected_answer"], answer, args.judge_model)
        else:
            score = heuristic_score(answer, row["expected_answer"])
        results.append({
            "id": row.get("id"),
            "question": row["question"],
            "expected_answer": row["expected_answer"],
            "generated_answer": answer,
            "sources": rag.get("sources", []),
            "score": score,
        })

    numeric_scores = []
    for r in results:
        s = r["score"].get("score")
        if isinstance(s, (int, float)):
            numeric_scores.append(float(s))
    report = {
        "num_questions": len(results),
        "judge_mode": args.judge,
        "average_score": mean(numeric_scores) if numeric_scores else None,
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Questions: {len(results)}")
    print(f"Average score: {report['average_score']}")
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
