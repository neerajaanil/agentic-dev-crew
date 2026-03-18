import ast
import re
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


def _strip_fences(text: str) -> str:
    """Remove markdown code fences so ast.parse sees clean Python."""
    text = re.sub(r"^```(?:python)?\s*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


class SyntaxValidatorInput(BaseModel):
    """Input schema for PythonSyntaxValidatorTool."""

    code: str = Field(
        ...,
        description="Python source code string to validate for syntax errors.",
    )


class PythonSyntaxValidatorTool(BaseTool):
    """Validates Python source code for syntax errors using the stdlib ast module.

    Agents should call this tool before delivering final code output to catch
    issues early — before they propagate to downstream tasks or output files.
    Markdown code fences are stripped automatically before parsing, so the tool
    also serves as a fence-detection signal.
    """

    name: str = "Validate Python Syntax"
    description: str = (
        "Validate a Python code string for syntax errors before writing it to a file. "
        "Pass the raw code (with or without markdown fences). "
        "Returns 'VALID' on success or a specific error message with line number."
    )
    args_schema: Type[BaseModel] = SyntaxValidatorInput

    def _run(self, code: str) -> str:
        cleaned = _strip_fences(code)
        try:
            ast.parse(cleaned)
            return "VALID: No syntax errors found."
        except SyntaxError as exc:
            return (
                f"SYNTAX ERROR at line {exc.lineno}: {exc.msg}\n"
                f"  >>> {exc.text}"
            )
