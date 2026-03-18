# Agents & Tasks Reference

Full documentation for the 5 agents and 5 tasks in the `agentic-dev-crew` pipeline.

---

## Agents

### 1. `engineering_lead`

| Property | Value |
|---|---|
| **Role** | Engineering Lead directing the software engineering team |
| **Default LLM** | `gpt-4o` (override: `LEAD_LLM` env var) |
| **Code Execution** | Disabled |
| **Tools** | None |

**Goal:** Transform high-level requirements into a precise, developer-ready technical design. Every class, method, and function must be specified with its signature, parameter types, return type, and a clear description. Edge cases and validation rules are called out explicitly so the backend engineer has no ambiguity.

**Why gpt-4o here:** Design is a reasoning-heavy task that benefits from strong instruction-following and structured output. gpt-4o produces well-organized Markdown specs with consistent formatting.

---

### 2. `backend_engineer`

| Property | Value |
|---|---|
| **Role** | Senior Python Engineer implementing production-quality code |
| **Default LLM** | `anthropic/claude-3-7-sonnet-latest` (override: `ENGINEER_LLM`) |
| **Code Execution** | Enabled (`safe` mode via Docker) |
| **Tools** | `FileWriterTool`, `PythonSyntaxValidatorTool` |
| **Max Execution Time** | 500 seconds |
| **Max Retries** | 3 |

**Goal:** Implement the engineering lead's design as clean, PEP-8-compliant Python with type hints and docstrings. The agent is instructed to call `PythonSyntaxValidatorTool` before delivering its final answer — this creates a self-validation loop that catches syntax errors before they reach the output file.

**Why claude-3-7-sonnet:** Excels at code generation tasks, producing clean Python with minimal markdown contamination when given explicit instructions.

**Code execution note:** The Docker sandbox lets the agent run Python snippets mid-task to verify logic. This is separate from the `PythonSyntaxValidatorTool` — the tool validates syntax, while code execution validates runtime behaviour.

---

### 3. `frontend_engineer`

| Property | Value |
|---|---|
| **Role** | Gradio UI specialist building prototype demos |
| **Default LLM** | `anthropic/claude-3-7-sonnet-latest` (override: `ENGINEER_LLM`) |
| **Code Execution** | Disabled |
| **Tools** | None |

**Goal:** Write a minimal, single-file Gradio application (`app.py`) that imports the backend class and exposes all its features. The UI must be runnable immediately with `python app.py` from the `output/` directory with no configuration.

**Design rationale:** Frontend code generation doesn't require runtime verification — the Gradio UI either renders or it doesn't, and incorrect UIs are caught quickly by inspection. Keeping code execution off here speeds up the pipeline.

---

### 4. `test_engineer`

| Property | Value |
|---|---|
| **Role** | QA Engineer writing comprehensive unit tests |
| **Default LLM** | `anthropic/claude-3-7-sonnet-latest` (override: `ENGINEER_LLM`) |
| **Code Execution** | Enabled (`safe` mode via Docker) |
| **Tools** | `FileWriterTool`, `PythonSyntaxValidatorTool` |
| **Max Execution Time** | 500 seconds |
| **Max Retries** | 3 |

**Goal:** Write a thorough `unittest` suite covering every public method — happy paths, all failure/error cases, and boundary conditions. Like the backend engineer, this agent self-validates syntax before delivery.

**Coverage expectations:** `setUp()` fixtures, one assertion per test method, explicit tests for every `return False` / exception path in the implementation.

---

### 5. `code_reviewer`

| Property | Value |
|---|---|
| **Role** | Staff Engineer conducting a thorough code review |
| **Default LLM** | `gpt-4o` (override: `REVIEWER_LLM`) |
| **Code Execution** | Disabled |
| **Tools** | None |
| **Context received** | Both `code_task` and `test_task` outputs |

**Goal:** Evaluate the implementation and test suite across seven dimensions: correctness, security, Python best practices, type safety, error handling, test quality, and performance. Produce a structured review with severity-ranked findings (Critical / Major / Minor / Suggestion) and a final verdict (Approve / Request Changes).

**Why this agent matters:** Most AI code generation pipelines stop at "it runs". The code reviewer adds an automatic quality gate that catches issues a human reviewer would flag — missing input validation, weak test assertions, unsafe operations, PEP 8 violations, and coverage gaps — without requiring a human in the loop.

**Why gpt-4o here:** Code review is a cross-cutting reasoning task that requires synthesising the design requirements, implementation details, and test coverage simultaneously. gpt-4o's strong reasoning makes it well-suited for identifying subtle gaps.

---

## Tasks

### 1. `design_task`

```
Agent:       engineering_lead
Context:     None (first in pipeline)
Output file: output/{module_name}_design.md
```

Produces a Markdown design document: module overview, class attribute tables, method signatures with parameter/return types, and explicit edge cases. No Python code — pure design.

---

### 2. `code_task`

```
Agent:       backend_engineer
Context:     design_task
Output file: output/{module_name}
```

Implements the design as raw Python source. The agent is explicitly instructed to output _only_ Python code — no markdown fences, no prose. The `postprocess_outputs()` function in `crew.py` strips any accidental fences as a safety net.

---

### 3. `frontend_task`

```
Agent:       frontend_engineer
Context:     code_task
Output file: output/app.py
```

Generates a Gradio `app.py` that imports the backend module. Single-user, prototype-grade UI that demonstrates all backend features. Runs with `python app.py`.

---

### 4. `test_task`

```
Agent:       test_engineer
Context:     code_task
Output file: output/test_{module_name}
```

Generates a `unittest` test file. Context is the implementation (not the design), so tests are written against actual signatures. The agent uses `PythonSyntaxValidatorTool` before finalising.

---

### 5. `review_task`

```
Agent:       code_reviewer
Context:     code_task + test_task
Output file: output/{module_name}_review.md
```

Receives both the implementation and tests as context for a holistic review. Output format:
- **Executive Summary** — 2–3 sentence quality assessment
- **Findings table** — Severity | Location | Issue | Recommendation
- **Top 3 Recommendations** — expanded detail on the most impactful changes
- **Verdict** — Approve / Request Changes

---

## Custom Tools

### `FileWriterTool`

```python
from agentic_dev_crew.tools import FileWriterTool
```

Writes content to `output/<filename>`. Path is resolved via `Path(__file__)` — always writes to the correct project `output/` directory regardless of the caller's working directory. Given to `backend_engineer` and `test_engineer` so they can persist files during code execution steps.

### `PythonSyntaxValidatorTool`

```python
from agentic_dev_crew.tools import PythonSyntaxValidatorTool
```

Runs `ast.parse()` on a code string and returns either `"VALID: No syntax errors found."` or a specific error message with line number and offending text. Strips markdown fences before parsing, so it also serves as a fence-detection signal. Given to the same agents that produce Python code.

---

## Post-Processing (`postprocess_outputs`)

Called from `main.py` after `crew.kickoff()` completes:

1. **Fence stripping** — iterates over all `*.py` files in `output/`, removes ```` ```python ```` and ```` ``` ```` fences, writes the cleaned version back.
2. **Run summary** — writes `output/run_summary.md` with a table of every generated file, its size, and a record of which files had fences stripped.

This is decoupled from the CrewAI framework and can be called independently or extended (e.g., to run `black` formatting, `pylint`, or `pytest` automatically).

---

## Configuration Reference

All configuration lives in YAML files under `agentic_dev_crew/config/`. LLMs are specified in `agents.yaml` as defaults and can be overridden at runtime via environment variables.

Template variables passed to `crew.kickoff(inputs=...)`:
- `{requirements}` — plain-English requirements text
- `{module_name}` — target Python filename (e.g. `accounts.py`)
- `{class_name}` — primary class name (e.g. `Account`)

These are interpolated into both agent goals and task descriptions via CrewAI's built-in template system, and also into `output_file` paths in `tasks.yaml`.
