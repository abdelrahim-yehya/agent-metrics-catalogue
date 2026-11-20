# Motivating example: course RAG chatbot, traced by Langfuse, scored by Phoenix and DeepEval

One run of 12 scripted questions (2026-10-28) through the "Course Materials RAG" chatbot from the DeepLearning.AI course *Claude Code: A Highly Agentic Coding Assistant* (one LLM with two tools, `search_course_content` and `get_course_outline`, over four course transcripts). The app ran on `gpt-5-mini`; its Langfuse instrumentation is the one in the local working copy of that course project. The starting point is the course's public code, https://github.com/https-deeplearning-ai/starting-ragchatbot-codebase (it uses Claude and has only the search tool); our version runs on `gpt-5-mini` and adds `get_course_outline`. Langfuse recorded tokens, cost, latency and tool calls. Phoenix evals and DeepEval then scored the recorded turns offline, with `gpt-5-mini` as judge. The picture is `results/metrics_matrix_20261028-104817.svg`.

This is a motivating illustration, not an evaluation of the tools: one run, one model as both app and judge, no human labels.

## Files

| File | What it is |
| --- | --- |
| `backend/`, `frontend/` | The chatbot: FastAPI app, retrieval (ChromaDB), the two tools, the model call with Langfuse tracing, and the web page. Start it with `run.sh` (`uv sync` installs `pyproject.toml`/`uv.lock`; Python 3.13) |
| `questions.py` | The 12 questions in 9 sessions, with expected answers taken from the transcripts and written before the run |
| `run_questions.py` | Runs them through the app in `backend/` (needs the course transcripts in `docs/`, not included) |
| `fetch_observations.py` | Assembles one record per turn from Langfuse (v2 observations API) |
| `evaluate_rag.py` | Phoenix and DeepEval evaluators over those records |
| `plot_matrix.py` | Draws the metric-by-tool matrix from the two files above and `results/metric_taxonomy.csv`; reproduces the SVG exactly |
| `export_measured_table.py` | Writes the paper's table of metrics reported in the run (`results/example_metrics.tex`) |
| `plot_run_sequence.py` | Draws the paper's Fig. 1, run S7 (the Kubernetes question) as an annotated sequence diagram: user, application, model and search tool, the recorded operations as bars with their durations, and the same run on a time axis. Numbers and arguments are read from `results/turns_*.json` and `results/run_*.json`; `--pdf` prints `paper/figures/run_s7_sequence.pdf` with headless Brave |
| `results/run_*.json` | Answers and sources per question |
| `results/turns_*.json` | Langfuse numbers per turn (tokens, cost, latency, tool calls) |
| `results/eval_*.csv` | Evaluator labels, scores and judge explanations |
| `results/metrics_matrix_*.svg` | The matrix |

## How to run it

You do not need to run it to check the paper: the recorded run is in `results/`. If you want to try the example yourself:

1. Install [uv](https://docs.astral.sh/uv/) and run `uv sync` in this folder (Python 3.13).
2. Put the course transcript text files in `docs/` (the course project's public code is linked above; the transcripts are not redistributed here).
3. Create a `.env` file next to the scripts. The run in the paper used OpenAI's `gpt-5-mini`, traced by a Langfuse project (cloud or self-hosted):

   ```
   LLM_PROVIDER=openai
   OPENAI_MODEL=gpt-5-mini
   OPENAI_API_KEY=<your OpenAI key>
   LANGFUSE_PUBLIC_KEY=<your Langfuse public key>
   LANGFUSE_SECRET_KEY=<your Langfuse secret key>
   LANGFUSE_BASE_URL=<your Langfuse URL, e.g. https://cloud.langfuse.com>
   ```

   `LLM_PROVIDER` can also be `anthropic` (set `ANTHROPIC_API_KEY`) or `ollama` (local, no key). Other models give other numbers.
4. Run the pipeline; each step writes into `results/`:

   ```bash
   uv run python run_questions.py                          # asks the 12 questions, traces go to Langfuse
   uv run python fetch_observations.py results/run_<tag>.json
   uv run pip install arize-phoenix-evals deepeval         # only needed for the evaluators
   uv run python evaluate_rag.py results/turns_<tag>.json
   uv run python plot_matrix.py results/turns_<tag>.json
   ```

To chat with the app instead, run `./run.sh` and open http://localhost:8000.

## Not included, and why

- The course transcripts (DeepLearning.AI material, expected in `docs/`), `.env` with API keys, and the vector store (`backend/chroma_db`). The app needs a `.env` with the provider, model, OpenAI and Langfuse keys.
- The retrieved transcript excerpts: tool outputs in `turns_*.json` are replaced by placeholders. `fetch_observations.py` regenerates them from Langfuse, but `evaluate_rag.py` needs the real outputs, so it cannot be rerun from this folder alone.

## Things to know when quoting the results

- `eval_*_before_friction_fix.csv` keeps the first User Friction results, which were wrong: the current turn was passed twice, so the judge read single questions as repeats (3 false positives). `eval_*_only.csv` is the corrected rerun, merged into `eval_*.csv`.
- DeepEval Task Completion scores plain questions as tasks to pose, so a correct answer can score low (for example 0.35 for "What is the capital of Australia?"). One caveat line in the paper covers this.
- One Phoenix Refusal call (S2) timed out and is excluded, so that cell counts 11 turns, not 12.
- On S7 the two Faithfulness evaluators disagree (Phoenix: unfaithful, DeepEval: 1.0); the matrix shows only their aggregates.
- Counts in the Langfuse column (tool calls, LLM calls, observations, errors) are computed from Langfuse observations; tokens, cost and latency are Langfuse's own values.
- The expected answer for S9 turn 3 was first written on a wrong prediction (that the app would forget); `questions.py` carries the corrected version and a comment.
