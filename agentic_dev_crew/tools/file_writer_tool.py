from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class FileWriterInput(BaseModel):
    """Input schema for FileWriterTool."""

    filename: str = Field(
        ...,
        description=(
            "The filename to write, relative to the output/ directory. "
            "Examples: 'accounts.py', 'test_accounts.py', 'app.py'."
        ),
    )
    content: str = Field(
        ...,
        description="The complete file content to write.",
    )


class FileWriterTool(BaseTool):
    """Writes content to a named file inside the project's output/ directory.

    Agents with code execution enabled can call this tool mid-task to persist
    intermediate or final artifacts without relying solely on task output_file.
    The output/ directory is resolved relative to the package root via __file__,
    so it is correct regardless of the caller's working directory.
    """

    name: str = "Write File"
    description: str = (
        "Write code or text content to a file in the output/ directory. "
        "Provide the filename (e.g. 'accounts.py') and the complete file content. "
        "The output/ directory is created automatically if it does not exist."
    )
    args_schema: Type[BaseModel] = FileWriterInput

    def _run(self, filename: str, content: str) -> str:
        output_dir = Path(__file__).resolve().parent.parent.parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        target = output_dir / filename
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content):,} characters to {target}"
