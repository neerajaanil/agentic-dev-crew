# agentic-dev-crew

> Autonomous software engineering crew powered by [CrewAI](https://github.com/crewAIInc/crewAI) — give it requirements, get back a complete Python module.

A production-grade multi-agent system that orchestrates **5 specialized AI agents** in a sequential pipeline to generate a fully-formed Python module from plain-English requirements:

| Output | Description |
|---|---|
| `{module}_design.md` | Technical design doc (classes, signatures, edge cases) |
| `{module}.py` | Production-quality Python implementation |
| `app.py` | Gradio demo UI — runs immediately |
| `test_{module}.py` | Comprehensive unittest suite |
| `{module}_review.md` | Staff-engineer code review with severity-ranked findings |
| `run_summary.md` | Audit trail of every generated artifact |

---

## Agent Pipeline

```
requirements + module_name + class_name
         │
         ▼
 ┌─────────────────┐
 │ engineering_lead│  gpt-4o
 │   design_task   │──► output/{module}_design.md
 └────────┬────────┘
          │ design as context
          ▼
 ┌─────────────────────┐
 │  backend_engineer   │  claude-3-7-sonnet
 │     code_task       │──► output/{module}.py
 │  [FileWriter +      │
 │  SyntaxValidator]   │
 └──────┬──────────────┘
        │ implementation as context
        ├─────────────────────────────────┐
        ▼                                 ▼
 ┌──────────────────┐          ┌──────────────────────┐
 │frontend_engineer │          │    test_engineer      │
 │  frontend_task   │          │      test_task        │
 │                  │          │  [FileWriter +        │
 └──────────────────┘          │   SyntaxValidator]    │
  output/app.py                └──────────────────────┘
                                output/test_{module}.py
        │                                 │
        └────────────┬────────────────────┘
                     │ code + tests as context
                     ▼
            ┌─────────────────┐
            │  code_reviewer  │  gpt-4o
            │   review_task   │──► output/{module}_review.md
            └─────────────────┘
                     │
                     ▼
              postprocess_outputs()
              • Strip markdown fences from .py files
              • Write output/run_summary.md
```

---

## What Makes This Production-Grade

| Design Choice | Why It Matters |
|---|---|
| **5th agent: code reviewer** | Automatic quality gate — every generated module gets a severity-ranked staff review |
| **`PythonSyntaxValidatorTool`** | Agents self-validate before delivering output, catching silent failures early |
| **`FileWriterTool`** | Code-execution agents can persist files mid-task, not just at task end |
| **Configurable LLMs via env vars** | Swap models without touching code — optimize for cost vs. capability per role |
| **Output post-processor** | Strips accidental markdown fences → generated code is always directly importable |
| **`run_summary.md`** | Lightweight audit trail for every run — file names, sizes, post-processing actions |
| **`argparse` CLI** | Reusable tool: inline requirements, file-based requirements, custom module/class names |
| **`Path(__file__)` resolution** | All paths are absolute relative to the package — works from any working directory |

---

## Setup

**Requirements:** Python 3.10–3.12, Docker (for agent code execution sandbox)

```bash
# 1. Clone and enter the project
git clone https://github.com/your-username/agentic-dev-crew.git
cd agentic-dev-crew

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env — add OPENAI_API_KEY and ANTHROPIC_API_KEY

# 5. Verify Docker is running (needed for code execution sandbox)
docker info
```

---

## Usage

### Default run (accounts management example)

```bash
python -m agentic_dev_crew.main
```

### Custom module — inline requirements

```bash
python -m agentic_dev_crew.main \
  --module-name orders.py \
  --class-name Order \
  --requirements "An order management system that tracks buy/sell orders for items, calculates totals, and enforces inventory limits."
```

### Custom module — requirements from file

```bash
python -m agentic_dev_crew.main \
  --module-name inventory.py \
  --class-name Inventory \
  --requirements-file my_requirements.txt
```

### Programmatic API

```python
from agentic_dev_crew import AgenticDevCrew
from agentic_dev_crew.crew import postprocess_outputs

inputs = {
    "requirements": "...",
    "module_name": "accounts.py",
    "class_name": "Account",
}
result = AgenticDevCrew().crew().kickoff(inputs=inputs)
postprocess_outputs("accounts.py")
print(result.raw)
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | Used by `engineering_lead` and `code_reviewer` (gpt-4o) |
| `ANTHROPIC_API_KEY` | Yes | — | Used by `backend_engineer`, `frontend_engineer`, `test_engineer` |
| `LEAD_LLM` | No | `gpt-4o` | Override LLM for engineering_lead |
| `ENGINEER_LLM` | No | `anthropic/claude-3-7-sonnet-latest` | Override LLM for backend/frontend/test engineers |
| `REVIEWER_LLM` | No | `gpt-4o` | Override LLM for code_reviewer |

---

## Running the Generated Output

```bash
cd output

# Run the Gradio demo UI
python app.py
# → Opens at http://localhost:7860

# Run the unit tests
python -m pytest test_accounts.py -v

# Validate Python syntax manually
python -c "import ast; ast.parse(open('accounts.py').read()); print('Syntax OK')"
```

---

## Project Structure

```
agentic-dev-crew/
├── agentic_dev_crew/
│   ├── __init__.py              # Package entry point, exports AgenticDevCrew
│   ├── main.py                  # CLI: argparse, load_dotenv, postprocess
│   ├── crew.py                  # @CrewBase orchestration + post-processing utils
│   ├── config/
│   │   ├── agents.yaml          # 5 agent definitions (role, goal, backstory, llm)
│   │   └── tasks.yaml           # 5 task definitions (descriptions, context, output_file)
│   └── tools/
│       ├── file_writer_tool.py  # BaseTool: writes files to output/
│       └── syntax_validator_tool.py  # BaseTool: validates Python via ast.parse
├── knowledge/
│   └── user_preference.txt      # Injected into agent context
├── output/                      # Generated artifacts (gitignored)
├── requirements.txt
├── .env.example
├── agents.md                    # Full agent/task documentation
└── README.md
```

---

## Notes

- Docker must be running for `backend_engineer` and `test_engineer` (they use `code_execution_mode="safe"`).
- Delete `output/` between runs to start fresh.
- The `code_reviewer` agent receives both the implementation and the test suite as context, enabling it to evaluate coverage completeness.
- LLM costs per run depend on model selection and requirements complexity. The default setup uses gpt-4o for reasoning-heavy roles and claude-3-7-sonnet for code generation.
