"""Verify pipeline fixes against gold SPARQL for previously failed eval questions."""
from __future__ import annotations

import json
from pathlib import Path

import nbformat

PROJECT_ROOT = Path(__file__).resolve().parent
FAILED_INDICES = [9, 26, 31, 71, 77, 78, 79, 80, 86]


def load_ns() -> dict:
    nb = nbformat.read(PROJECT_ROOT / "graphdb_ontology_qa.ipynb", as_version=4)
    g: dict = {}
    for idx in (2, 4, 5):
        exec(compile(nb.cells[idx].source, f"cell{idx}", "exec"), g)
    return g


def gold_by_question() -> dict[str, dict]:
    dataset = PROJECT_ROOT / "qa_eval_dataset.jsonl"
    by_q: dict[str, dict] = {}
    for line in dataset.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            by_q[row["question"]] = row
    return by_q


def main() -> None:
    ns = load_ns()
    questions = [
        line.strip()
        for line in (PROJECT_ROOT / "qa_eval_questions.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gold = gold_by_question()
    is_valid = ns["is_likely_valid_sparql"]
    normalize = ns["normalize_sparql"]
    run_sparql = ns["run_sparql"]
    has_results = ns["sparql_has_results"]

    print("Gold SPARQL validation + GraphDB execution for failed indices:\n")
    for q_idx in FAILED_INDICES:
        question = questions[q_idx - 1]
        row = gold[question]
        q = normalize(row["sparql"])
        ok, reason = is_valid(q)
        status = "VALID" if ok else f"INVALID ({reason})"
        rows = "n/a"
        if ok:
            try:
                result = run_sparql(q)
                rows = "yes" if has_results(result, q) else "no"
            except Exception as e:
                rows = f"exec error: {e}"
        print(f"Q{q_idx}: {status}; rows={rows}")

    # Card rewrite smoke test
    bad = 'SELECT ?type WHERE { ?card a core:Card . ?card core:card_type ?type . }'
    fixed = ns["fix_instance_data_patterns"](bad)
    print(f"\nCard rewrite contains events_cards: {'events_cards' in fixed}")

    # ASK + nested SELECT smoke test
    ask_nested = """PREFIX core: <https://w3id.org/football-cdf/core#>
ASK WHERE {
  { SELECT (COUNT(?c) AS ?n) WHERE { ?m core:events_cards ?c } }
}"""
    ok, reason = is_valid(ask_nested)
    print(f"ASK+nested SELECT valid: {ok} ({reason})")


if __name__ == "__main__":
    main()
