# Motivating example: course RAG chatbot, traced by Langfuse, scored by Phoenix and DeepEval

One run of 12 scripted questions (2026-10-28) through the "Course Materials RAG" chatbot from the DeepLearning.AI course *Claude Code: A Highly Agentic Coding Assistant* (one LLM with two tools, `search_course_content` and `get_course_outline`, over four course transcripts). The app ran on `gpt-5-mini`; its Langfuse instrumentation is the one in the local working copy of that course project. The starting point is the course's public code, https://github.com/https-deeplearning-ai/starting-ragchatbot-codebase (it uses Claude and has only the search tool); our version runs on `gpt-5-mini` and adds `get_course_outline`. Langfuse recorded tokens, cost, latency and tool calls. Phoenix evals and DeepEval then scored the recorded turns offline, with `gpt-5-mini` as judge. The picture is `results/metrics_matrix_20261028-104817.svg`.

This is a motivating illustration, not an evaluation of the tools: one run, one model as both app and judge, no human labels.

## Files

The scripts that ran and plotted the example are not part of this repository; only the recorded results are.

| File | What it is |
| --- | --- |
| `results/run_*.json` | Questions, answers and sources per question |
| `results/turns_*.json` | Langfuse numbers per turn (tokens, cost, latency, tool calls) |
| `results/eval_*.csv` | Evaluator labels, scores and judge explanations |
| `results/metrics_matrix_*.svg`, `.pdf` | The metric-by-tool matrix |
| `results/metrics_measured_*.svg`, `.pdf` | The metrics reported in the run, by tool |
| `results/run_s7_sequence.svg` | Run S7 (the Kubernetes question) as an annotated sequence diagram |
| `results/langfuse_graph_s7.svg` | The same run as one chain, redrawn from Langfuse's agent graph |

## Not included, and why

- The course project and its transcripts (DeepLearning.AI material), `.env` with API keys, and the vector store.
- The retrieved transcript excerpts: tool outputs in `turns_*.json` are replaced by placeholders.
- The scripts (question runner, Langfuse export, evaluators and plots).

## Things to know when quoting the results

- `eval_*_before_friction_fix.csv` keeps the first User Friction results, which were wrong: the current turn was passed twice, so the judge read single questions as repeats (3 false positives). `eval_*_only.csv` is the corrected rerun, merged into `eval_*.csv`.
- DeepEval Task Completion scores plain questions as tasks to pose, so a correct answer can score low (for example 0.35 for "What is the capital of Australia?"). One caveat line in the paper covers this.
- One Phoenix Refusal call (S2) timed out and is excluded, so that cell counts 11 turns, not 12.
- On S7 the two Faithfulness evaluators disagree (Phoenix: unfaithful, DeepEval: 1.0); the matrix shows only their aggregates.
- Counts in the Langfuse column (tool calls, LLM calls, observations, errors) are computed from Langfuse observations; tokens, cost and latency are Langfuse's own values.
- The expected answer for S9 turn 3 was first written on a wrong prediction (that the app would forget); the corrected version is the one used in the results.
