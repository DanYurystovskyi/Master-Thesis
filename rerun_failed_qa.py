"""Re-run GraphDB QA for failed eval question indices and merge into JSONL."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat

PROJECT_ROOT = Path(__file__).resolve().parent
FAILED_INDICES = [9, 26, 31, 71, 77, 78, 79, 80, 86]


def exec_notebook_cells() -> dict:
    nb_path = PROJECT_ROOT / "graphdb_ontology_qa.ipynb"
    nb = nbformat.read(nb_path, as_version=4)
    g: dict = {"__name__": "__main__"}
    for idx in (2, 3, 4, 5):
        src = nb.cells[idx].source
        if idx == 1:
            continue
        exec(compile(src, f"{nb_path.name}:cell{idx}", "exec"), g)
    return g


def main() -> int:
    print("Loading notebook pipeline...")
    ns = exec_notebook_cells()

    questions_path = PROJECT_ROOT / "qa_eval_questions.txt"
    output_path = PROJECT_ROOT / "qa_eval_graphdb_outputs.jsonl"
    all_questions = [
        line.strip()
        for line in questions_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    load_existing_records = ns["load_existing_records"] if "load_existing_records" in ns else None
    if load_existing_records is None:
        def load_existing_records(path: Path) -> dict[int, dict]:
            records: dict[int, dict] = {}
            if not path.exists():
                return records
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                q_idx = record.get("question_index")
                if q_idx is None and record.get("question") in all_questions:
                    q_idx = all_questions.index(record["question"]) + 1
                if q_idx is None:
                    q_idx = -line_no
                records[int(q_idx)] = record
            return records

    run_qa_record = ns["run_qa_record"] if "run_qa_record" in ns else None
    if run_qa_record is None:
        generate_sparql = ns["generate_sparql"]
        run_sparql_safe = ns["run_sparql_safe"]
        answer_from_results = ns["answer_from_results"]
        schema_hint = ns["schema_hint"]

        def run_qa_record(question: str, question_index: int) -> dict:
            record = {
                "question_index": question_index,
                "question": question,
                "initial_sparql": None,
                "sparql": None,
                "answer": None,
                "error": None,
            }
            try:
                initial_sparql = generate_sparql(question, schema_hint)
                record["initial_sparql"] = initial_sparql
                final_sparql, result_json = run_sparql_safe(
                    question, initial_sparql, schema_hint
                )
                record["sparql"] = final_sparql
                record["answer"] = answer_from_results(
                    question, final_sparql, result_json
                )
            except Exception as e:
                record["error"] = str(e)
            return record

    existing_records = load_existing_records(output_path)
    batch_results: list[dict] = []

    for q_idx in FAILED_INDICES:
        if q_idx < 1 or q_idx > len(all_questions):
            print(f"Skip invalid index {q_idx}")
            continue
        question = all_questions[q_idx - 1]
        preview = question if len(question) <= 100 else question[:97] + "..."
        print(f"\n[{q_idx}/{len(all_questions)}] {preview}")
        record = run_qa_record(question, q_idx)
        prev = existing_records.get(q_idx)
        if record.get("error") and "Connection error" in str(record["error"]):
            if prev and not (
                prev.get("error") and "Connection error" in str(prev.get("error"))
            ):
                print("  SKIP merge (connection error; keeping previous record)")
                batch_results.append(prev)
                continue
        existing_records[q_idx] = record
        batch_results.append(record)
        if record["error"]:
            print("  ERROR:", record["error"])
        else:
            answer_preview = (record["answer"] or "").replace("\n", " ")
            if len(answer_preview) > 120:
                answer_preview = answer_preview[:117] + "..."
            print("  ANSWER:", answer_preview)

    with output_path.open("w", encoding="utf-8") as f:
        for q_idx in sorted(existing_records):
            f.write(json.dumps(existing_records[q_idx], ensure_ascii=False) + "\n")

    ok = sum(1 for r in batch_results if not r["error"])
    failed = len(batch_results) - ok
    print(
        f"\nDone. Merged {len(batch_results)} record(s) into {output_path.name} "
        f"({ok} ok, {failed} failed in this batch; {len(existing_records)} total in file)."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
