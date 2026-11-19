# Observability re-check: procedure (2026-11-13)

This is the procedure given to each reviewer. It is kept as the record of what was done.

## Why
`results/built_in_metrics.csv` holds the built-in metrics found in each tool's official documentation. The first collection recorded what a page presents as a metric (a heading, a table row, a named field). It missed values a tool records automatically but mentions only in passing: Langfuse's cached-token usage type appears inside a sentence as an example and was not recorded. The 18 observability metrics (tokens, cost, latency, errors, counts, tool calls) are the ones exposed to this, because tools often record them without calling them metrics. This review re-checks every observability cell of the tool-by-metric matrix that is not "built-in" today.

## Input
- `data/interim/observability_recheck/open_cells.csv`: the 127 open cells (tool, metric, our definition of the metric).
- `data/interim/observability_recheck/snapshots/<toolslug>__*.txt`: pages downloaded on 2026-11-13 (tracing, data model, token and cost, dashboards, monitoring, alerts); `fetch_log.csv` gives the URL of each file.
- `data/raw/doc_snapshots/<toolslug>__*.txt`: the pages already cited in the dataset (file name -> URL: column `doc_url` of `results/built_in_metrics.csv`).
- `results/built_in_metrics.csv` filtered by `tool`: what is already recorded; `data/inputs/taxonomy_mapping.csv`: which unique metric each recorded row maps to.
- `data/interim/changelog_review/review_decisions.csv`: changelog entries already reviewed. Do not re-propose a changelog entry that was "not added" there.

## What to do, per tool
For each open cell of the tool, decide whether the documentation states that the tool provides that metric built-in. Work economically: never print whole files. Shortlist with `grep -n -i -E` on the terms of the metric (and the tool's own vocabulary), then read each shortlisted passage with a line range wide enough to know what the page is describing.
If a page you read links to another page of the same documentation that clearly describes the missing value (for example a span attribute reference or a usage schema), download it with `curl -sL` (the `.md` URL where the site offers one; never a summarising fetch tool), save it in `data/interim/observability_recheck/snapshots/` with the same naming, and add a line to `fetch_log.csv`. Do not search the web beyond the tool's own documentation and official repository.

## Rules that decide the verdict
- **built-in**: the page states that the tool itself records, computes or displays the value with no code or query written by the user: a field of the trace or span data model that the tool fills automatically, a named column, filter, chart metric, preset dashboard, alert metric, or a named attribute a set of conventions defines. Automatic capture through the tool's own instrumentation of at least some providers or frameworks counts.
- **custom**: the value is reachable only by something the user writes or assembles: an SQL or query example, a formula, a custom dashboard described as a use case, a value the user must pass in by hand.
- **mentioned only**: the words appear, but in a guide, a comparison, a bug fix or an example that does not state the tool provides the value.
- **not found**: nothing in the pages read.
- The value must fit OUR definition of the metric in `open_cells.csv`. A request count is not a tool call count; a session duration is not a trace latency unless the page equates them; the latency of every span is "Span duration", not "LLM call latency", unless the page names model calls or generations. When the fit is doubtful, give the verdict you find most defensible, set `confidence` to `low` and explain in `note`.
- Be conservative. A wrong "built-in" is worse than a missed one. Do not infer a metric from a screenshot caption, an image alt text or a code sample alone unless the sentence around it states what the tool records.

## Evidence rules (strict)
- For a **built-in** or **custom** verdict, `quote` is copied verbatim from the saved file, is at least 20 characters and names the value. Verify each quote before finishing (whitespace collapsed on both sides):
  `python3 -c "import re,sys; t=re.sub(r'\s+',' ',open(sys.argv[1],encoding='utf-8',errors='replace').read()); q=re.sub(r'\s+',' ',sys.argv[2]).strip(); print(len(q)>=20 and q in t)" <snapshot> "<quote>"`
- `doc_url` is the public URL of the page (without a trailing `.md` when the page also exists without it; keep the URL from `fetch_log.csv` otherwise).

## Output (write only inside `data/interim/observability_recheck/`; nothing else in the repository is edited; do not commit)
Per tool, `<toolslug>__cells.csv`, written with Python's `csv` module, one row per open cell of that tool, columns:
`tool,metric,verdict,tool_specific_name,doc_url,snapshot_file,quote,note,confidence`
- `verdict`: `built-in`, `custom`, `mentioned only` or `not found`
- `tool_specific_name`: the tool's own name for the value (for built-in), as it would be recorded in `metric_name`
- `note`: for `not found` and `mentioned only`, which files were searched and with which terms; for the others, anything that qualifies the claim
- `confidence`: `high` or `low`
If, while reading, you see a built-in observability value that is recorded for the tool under a WRONG unique metric, or a recorded row whose quote no longer supports it, add a line to `<toolslug>__remarks.txt`.

## Report (under 300 words)
Per tool: the cells with verdict built-in (metric -> the tool's name, confidence), the cells that are custom, and anything that could not be checked. No page contents.
