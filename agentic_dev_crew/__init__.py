"""agentic-dev-crew

Autonomous software engineering crew powered by CrewAI.

Takes plain-English requirements and orchestrates a 5-agent pipeline to produce:
  - A technical design document
  - A production-quality Python implementation
  - A Gradio demo UI
  - A comprehensive unit test suite
  - A staff-engineer code review

Usage::

    from agentic_dev_crew import AgenticDevCrew

    result = AgenticDevCrew().crew().kickoff(inputs={
        "requirements": "...",
        "module_name": "my_module.py",
        "class_name": "MyClass",
    })
"""

__all__ = ["AgenticDevCrew"]

from .crew import AgenticDevCrew
