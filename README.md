# Master Thesis — Football KG Question Answering

Question answering over a football knowledge graph built from [StatsBomb open data](https://github.com/statsbomb/open-data), with multiple QA approaches and automated evaluation against a gold dataset (92 questions).

## Prerequisites

- **StatsBomb open data** — clone or download [statsbomb/open-data](https://github.com/statsbomb/open-data) locally (not included in this repo).
- **Python 3.10+** and Jupyter.
- **GraphDB** — for the SPARQL-based approaches (`graphdb_ontology_qa`, hybrid GraphDB route). Default endpoint: `http://localhost:7200/repositories/Master_Thesis`.
- **LLM API access** — QA notebooks use an OpenAI-compatible API (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`). Ragas evaluation also requires `OPENAI_API_KEY` for the LLM judge.

Install dependencies:

```bash
pip install -r requirements.txt
```

If `torch` fails to install, install PyTorch for your platform from [pytorch.org](https://pytorch.org) first, then rerun the command above.

## Scripts from `statsbomb-to-football-cdf`

Adapted from [wu-semsys/statsbomb-to-football-cdf](https://github.com/wu-semsys/statsbomb-to-football-cdf):

- `transform_to_football_cdf.py` — StatsBomb JSON → CDF JSON
- `football_cdf_to_jsonld.py` — CDF JSON → JSON-LD

## Pipeline overview

| Step | Notebook | Purpose |
|------|----------|---------|
| 1 | `cdf_combining.ipynb` | Combine per-match CDF JSON from `cdf_batch_output/` |
| 2 | `kg_linearization.ipynb` | Linearize KG triples → `fcdf_kg_triples_linearized.jsonl` |
| 3 | `ontology_inspection.ipynb` | Inspect classes/properties in `ontology.ttl` |
| 4 | QA notebooks (below) | Answer eval questions, write `qa_eval_*_outputs.jsonl` |
| 5 | `bertscore_eval.ipynb` | BERTScore vs gold answers |
| 6 | `ragas_eval.ipynb` | Ragas metrics (faithfulness, answer relevancy, answer correctness) |

Large generated files (`*.json`, `*.jsonl`, Chroma DB folders, TTL exports) are **local only** — see `.gitignore`.

## QA approaches

Each approach writes batch predictions to `qa_eval_<approach>_outputs.jsonl` (with `contexts` for Ragas).

| Approach | Notebook | Output file |
|----------|----------|-------------|
| GraphDB + SPARQL | `graphdb_ontology_qa.ipynb` | `qa_eval_graphdb_outputs.jsonl` |
| RAG (with events) | `kg_triples_rag.ipynb` (`ACTIVE_PROFILE=with_events`) | `qa_eval_rag_with_events_outputs.jsonl` |
| RAG (no events) | `kg_triples_rag.ipynb` (`ACTIVE_PROFILE=no_events`) | `qa_eval_rag_no_events_outputs.jsonl` |
| Hybrid (GraphDB + RAG router) | `hybrid_kg_qa.ipynb` | `qa_eval_hybrid_outputs.jsonl` |
| CDF JSON RAG | `cdf_json_rag.ipynb` | `qa_eval_cdf_json_rag_outputs.jsonl` |

**RAG indexing:** run the indexing cells in `kg_triples_rag.ipynb` before RAG or hybrid batch eval. Profiles persist to `chroma_db_with_events/` and `chroma_db_no_events/`. Hybrid without events uses `chroma_db_no_events/` and collection `kg_entities_no_events`.

**Batch eval:** all QA notebooks use `qa_eval_questions.txt` / `qa_eval_dataset.jsonl`. Runs are resumable (incremental append to output JSONL).

Question templates are documented in `qa_template_bank.md`.

## Evaluation

### BERTScore (`bertscore_eval.ipynb`)

Set `APPROACH` or `RUN_ALL_APPROACHES = True`. Writes per-approach results and `qa_eval_bertscore_all_approaches_summary.json`.

### Ragas (`ragas_eval.ipynb`)

Set `OPENAI_API_KEY` in your environment (never commit keys). Set `APPROACH` or `RUN_ALL_APPROACHES = True`. Uses stored `contexts` from QA outputs (GraphDB has SPARQL fallback for legacy rows). Writes `qa_eval_ragas_*` results and `qa_eval_ragas_all_approaches_summary.json`.

## Past work

`Past tries/` holds earlier experiments (Neo4j import, LangChain RAG, linewise RAG, etc.) and is kept for reference.
