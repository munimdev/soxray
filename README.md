# Soxray

A small **proof-of-concept** for running **Sarbanes–Oxley (SOX) style control tests** with an LLM: you define a control, point the runner at **CSV evidence**, and a **LangGraph** agent uses a fixed toolset to walk the test procedure, record structured **pass/exception** findings, and write an audit-style **PDF workpaper** under `output/`.

## What it does

- **Controls as data** — Each control is a `ControlDefinition` (narrative, test steps, `threshold_rules` for things like time windows and variance). Adding a new control is mostly configuration, not a rewrite of the agent.
- **Agent + tools** — The model calls tools to load evidence, join datasets, run batch math (`calculate_deltas`), record findings in one shot (`flag_findings_batch`), and **generate a workpaper** from accumulated context. Workpaper text can surface a business-friendly `workpaper_test_summary` so the PDF stays readable for non-technical readers.
- **Findings** — Results use a structured `TestFinding` model, including an optional `control_owner_response` field to reflect that a workpaper often continues into **management / audit review** after the run.

## Sample controls (included)

| ID         | Name                       | Idea                                                                     |
| ---------- | -------------------------- | ------------------------------------------------------------------------ |
| `ITGC-001` | User access deprovisioning | HR terminations vs. AD events (e.g. account disabled after termination). |
| `BPC-001`  | Invoice 3-way match        | Invoices vs. POs: variance and missing-PO checks within tolerance rules. |

## Requirements

- Python **3.11+** (see `pyproject.toml` for the upper bound)
- [Poetry](https://python-poetry.org/) for dependencies
- An **OpenAI API key** (the agent uses the Chat Completions–compatible API via `langchain-openai`)

## Setup

From the repository root:

```bash
poetry install
cp sample.env .env
# Edit .env and set OPENAI_API_KEY=...
```

A `poetry.toml` in the repo uses an **in-project** virtualenv (`.venv/`). If you use `poetry shell`, run commands from the repo root so paths like `data/` and `output/` resolve correctly.

## Run a control

```bash
poetry run python main.py ITGC-001
# or
poetry run python main.py BPC-001
```

The CLI loads evidence paths wired in `main.py` for each control, streams the graph, and prints the path to the generated PDF (for example `output/workpaper_itgc-001.pdf`) when `generate_workpaper` succeeds.

## Synthetic data (optional)

To regenerate CSVs under `data/`:

```bash
poetry run python scripts/generate_data.py
```

## Layout

| Path      | Role                                                                                                    |
| --------- | ------------------------------------------------------------------------------------------------------- |
| `soxray/` | Package: agent graph, tools, Pydantic models, control definitions.                                      |
| `data/`   | Example CSV evidence.                                                                                   |
| `output/` | Generated PDF workpapers (you may add `output/` to `.gitignore` if you do not want to track artifacts). |
| `main.py` | CLI entry and prompt wiring.                                                                            |

## Development

```bash
poetry run ruff check .
poetry run mypy .
```
