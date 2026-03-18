"""Core crew orchestration for agentic-dev-crew.

This module wires together the 5-agent sequential pipeline and provides
post-processing utilities that run after the crew completes:

  1. Strip accidental markdown fences from generated .py files
     (some LLMs add them despite explicit instructions not to).
  2. Write output/run_summary.md — a lightweight audit trail of every
     generated file with its byte size and any fence-stripping actions taken.

Both functions are intentionally decoupled from the CrewAI framework so they
can be called, tested, or extended independently.
"""

import os
import re
from datetime import datetime
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from .tools.file_writer_tool import FileWriterTool
from .tools.syntax_validator_tool import PythonSyntaxValidatorTool

# ---------------------------------------------------------------------------
# Project root (two levels up from this file: agentic_dev_crew/ → project root)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_llm(env_var: str, default: str) -> str:
    """Return an LLM identifier from an env var, falling back to *default*.

    This makes every agent's model swappable at runtime without touching code:
      LEAD_LLM=anthropic/claude-opus-4-6 python -m agentic_dev_crew.main
    """
    return os.getenv(env_var, default)



def _strip_fences(text: str) -> str:
    """Remove markdown code fences from a string.

    Handles both ```python and plain ``` variants, with or without trailing
    whitespace, so the result is always clean, importable Python source.
    """
    text = re.sub(r"^```(?:python)?\s*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


# ---------------------------------------------------------------------------
# Crew definition
# ---------------------------------------------------------------------------

@CrewBase
class AgenticDevCrew:
    """5-agent sequential pipeline: design → code → UI → tests → review.

    Given plain-English requirements, the crew produces a complete Python module:
    - Design document     (output/{module_name}_design.md)
    - Implementation      (output/{module_name})
    - Gradio demo UI      (output/app.py)
    - Unit tests          (output/test_{module_name})
    - Code review         (output/{module_name}_review.md)

    LLMs are configurable via environment variables (LEAD_LLM, ENGINEER_LLM,
    REVIEWER_LLM) with sensible defaults, allowing cost/capability trade-offs
    without code changes.
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    @agent
    def engineering_lead(self) -> Agent:
        return Agent(
            config=self.agents_config["engineering_lead"],
            verbose=True,
            llm=_get_llm("LEAD_LLM", "gpt-4o"),
        )

    @agent
    def backend_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["backend_engineer"],
            verbose=True,
            llm=_get_llm("ENGINEER_LLM", "anthropic/claude-3-7-sonnet-latest"),
            tools=[FileWriterTool(), PythonSyntaxValidatorTool()],
        )

    @agent
    def frontend_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_engineer"],
            verbose=True,
            llm=_get_llm("ENGINEER_LLM", "anthropic/claude-3-7-sonnet-latest"),
        )

    @agent
    def test_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["test_engineer"],
            verbose=True,
            llm=_get_llm("ENGINEER_LLM", "anthropic/claude-3-7-sonnet-latest"),
            tools=[FileWriterTool(), PythonSyntaxValidatorTool()],
        )

    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["code_reviewer"],
            verbose=True,
            llm=_get_llm("REVIEWER_LLM", "gpt-4o"),
        )

    # ------------------------------------------------------------------
    # Tasks  (order here == execution order for sequential process)
    # ------------------------------------------------------------------

    @task
    def design_task(self) -> Task:
        return Task(config=self.tasks_config["design_task"])

    @task
    def code_task(self) -> Task:
        return Task(config=self.tasks_config["code_task"])

    @task
    def frontend_task(self) -> Task:
        return Task(config=self.tasks_config["frontend_task"])

    @task
    def test_task(self) -> Task:
        return Task(config=self.tasks_config["test_task"])

    @task
    def review_task(self) -> Task:
        return Task(config=self.tasks_config["review_task"])

    # ------------------------------------------------------------------
    # Crew
    # ------------------------------------------------------------------

    @crew
    def crew(self) -> Crew:
        """Assemble the sequential 5-agent crew and ensure output/ exists."""
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
        )


# ---------------------------------------------------------------------------
# Post-processing (called from main.py after crew.kickoff())
# ---------------------------------------------------------------------------

def postprocess_outputs(module_name: str) -> None:
    """Clean generated .py files and write an audit summary.

    Args:
        module_name: The module filename passed to kickoff (e.g. 'accounts.py').
                     Used to label the run summary.
    """
    output_dir = BASE_DIR / "output"
    if not output_dir.exists():
        return

    # Strip markdown fences from any .py files an LLM accidentally wrapped
    fence_cleaned: list[str] = []
    for py_file in sorted(output_dir.glob("*.py")):
        original = py_file.read_text(encoding="utf-8")
        cleaned = _strip_fences(original)
        if cleaned != original:
            py_file.write_text(cleaned, encoding="utf-8")
            fence_cleaned.append(py_file.name)

    # Write lightweight run summary
    lines: list[str] = [
        "# Run Summary\n\n",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n",
        f"**Module:** `{module_name}`\n\n",
        "## Output Files\n\n",
        "| File | Size |\n",
        "|------|------|\n",
    ]
    for f in sorted(output_dir.iterdir()):
        if f.is_file() and f.name != "run_summary.md":
            lines.append(f"| `{f.name}` | {f.stat().st_size:,} bytes |\n")

    if fence_cleaned:
        files_list = ", ".join(f"`{n}`" for n in fence_cleaned)
        lines.append(
            f"\n## Post-Processing\n\n"
            f"Stripped markdown fences from: {files_list}\n"
        )

    (output_dir / "run_summary.md").write_text("".join(lines), encoding="utf-8")
