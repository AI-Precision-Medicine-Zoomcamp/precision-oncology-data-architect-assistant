"""LLM answer evaluation with a simple rubric.

This script can run in two modes:
1. heuristic mode (default): checks if answer mentions key terms from expected answer.
2. llm judge mode: set --judge and OPENAI_API_KEY to score answers with an LLM.

Usage:
    python evaluation/llm_eval.py --questions evaluation/ground_truth.csv --limit 5
    python evaluation/llm_eval.py --use-llm --judge --limit 5
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

from src.api.service import run_assistant


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


def evaluation_text(rag: dict, use_llm: bool) -> str:
    """Return generated answer text or retrieved context for offline smoke eval."""
    if use_llm:
        return str(rag.get("answer", ""))
    return "\n\n".join(
        str(context.get("content", ""))
        for context in rag.get("contexts", [])
    )


def evaluate_rows(rows: list[dict], use_llm: bool, judge: bool, judge_model: str) -> dict:
    client = OpenAI() if judge else None
    results = []
    for row in rows:
        rag = run_assistant(row["question"], use_llm=use_llm)
        answer = rag["answer"]
        text_to_score = evaluation_text(rag, use_llm)
        if judge and client:
            score = judge_score(
                client,
                row["question"],
                row["expected_answer"],
                text_to_score,
                judge_model,
            )
        else:
            score = heuristic_score(text_to_score, row["expected_answer"])
        results.append({
            "id": row.get("id"),
            "question": row["question"],
            "expected_answer": row["expected_answer"],
            "generated_answer": answer,
            "evaluated_text_kind": "generated_answer" if use_llm else "retrieved_context",
            "sources": rag.get("sources", []),
            "score": score,
        })

    numeric_scores = []
    for result in results:
        score = result["score"].get("score")
        if isinstance(score, (int, float)):
            numeric_scores.append(float(score))
    return {
        "num_questions": len(results),
        "use_llm": use_llm,
        "judge_mode": judge,
        "average_score": mean(numeric_scores) if numeric_scores else None,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=Path("evaluation/ground_truth.csv"))
    parser.add_argument("--out", type=Path, default=Path("evaluation/llm_eval_results.json"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--judge-model", default=os.getenv("OPENAI_JUDGE_MODEL", "gpt-4o-mini"))
    parser.add_argument(
        "--compare-modes",
        action="store_true",
        help="Compare retrieval-context scoring with generated-answer scoring.",
    )
    args = parser.parse_args()

    load_dotenv()
    rows = load_rows(args.questions)
    if args.limit:
        rows = rows[: args.limit]

    if args.compare_modes:
        modes = {
            "retrieved_context": evaluate_rows(rows, use_llm=False, judge=args.judge, judge_model=args.judge_model),
            "generated_answer": evaluate_rows(rows, use_llm=True, judge=args.judge, judge_model=args.judge_model),
        }
        best_mode = max(
            modes,
            key=lambda mode: modes[mode]["average_score"]
            if modes[mode]["average_score"] is not None
            else -1,
        )
        report = {
            "comparison_type": "answer_mode",
            "best_mode": best_mode,
            "modes": modes,
        }
    else:
        report = evaluate_rows(
            rows,
            use_llm=args.use_llm,
            judge=args.judge,
            judge_model=args.judge_model,
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.compare_modes:
        print(f"Best mode: {report['best_mode']}")
    else:
        print(f"Questions: {report['num_questions']}")
        print(f"Average score: {report['average_score']}")
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
