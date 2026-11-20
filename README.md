# Agent Metrics Catalogue

Data and companion website for a study of observability and evaluation tooling for AI agents: which tools are most widely named, and which agent-execution metrics each one ships built in. Every claim has a source URL, a verbatim quote and an access date.

## Contents

| Folder | Content |
|---|---|
| `site/` | The static companion website (plain HTML, relative links). Open `site/index.html`, or run `python3 -m http.server -d site 8000`. Published with GitHub Pages by `.github/workflows/pages.yml`. |
| `results/` | The deliverables: `best_tools.csv` (16 entries: 13 tools and 3 standards), `built_in_metrics.csv` (298 built-in metric rows with URL, quote, snapshot and access date), `metric_taxonomy.csv` (45 unique metrics), `tool_metric_matrix*.csv/.html`, `standards_only_metrics.csv`, and the taxonomy figures (`.svg`). |
| `data/` | The evidence: `inputs/` (search logs, taxonomy mapping and definitions), `raw/` (GitHub search snapshot of 2026-10-22 and `doc_snapshots/`, plain-text copies of every documentation page quoted), `interim/` (screening tables and review records), `outputs/` (screening and relevance verdicts). |
| `example_rag/` | The worked example: a course chatbot asked twelve scripted questions, traced with Langfuse and scored with Arize Phoenix and DeepEval evaluators. The scripts, the recorded runs, the evaluation scores and the figures; see `example_rag/README.md`. The course transcripts, `.env` keys and vector store are not included. |
| `src/` | The scripts (Python 3, standard library only) that build the taxonomy, the tool-by-metric matrix, the tool table, the taxonomy figures and the site from the data, check every quote, and ran the GitHub search. |
| `docs/` | The written rules: `search_protocol.md`, `screening_rules.md` and `rule_index.md`. |

## Rebuilding

```bash
python3 src/build_taxonomy.py   # data/inputs/taxonomy_*.csv -> results/metric_taxonomy.csv
python3 src/build_matrix.py     # tool x metric matrix
python3 src/check_quotes.py     # every quote must appear verbatim in its saved page
python3 src/build_site.py       # the companion website in site/
```

`src/github_tool_search.py` repeats the live GitHub search; stars and dates change daily, so `data/raw/github_raw_results.csv` is the frozen snapshot the selection rests on.

## How to check a claim

Each row of `results/built_in_metrics.csv` names a file in `data/raw/doc_snapshots/`; its `quote` appears verbatim in that file.

## Notes

- Stars, downloads and activity dates are a frozen snapshot, not live values.
