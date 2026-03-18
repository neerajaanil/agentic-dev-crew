#!/usr/bin/env python
"""CLI entry point for the Agentic Dev Crew.

Run the crew with the built-in example:
    python -m agentic_dev_crew.main

Run with custom requirements inline:
    python -m agentic_dev_crew.main \\
        --module-name orders.py \\
        --class-name Order \\
        --requirements "An order management system..."

Run with requirements from a file:
    python -m agentic_dev_crew.main \\
        --module-name inventory.py \\
        --class-name Inventory \\
        --requirements-file my_requirements.txt
"""

import argparse
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

from .crew import AgenticDevCrew, postprocess_outputs

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# ---------------------------------------------------------------------------
# Default example — accounts management system for a trading simulation
# ---------------------------------------------------------------------------

_DEFAULT_REQUIREMENTS = """
A simple account management system for a trading simulation platform.
The system should allow users to create an account, deposit funds, and withdraw funds.
The system should allow users to record that they have bought or sold shares, providing a quantity.
The system should calculate the total value of the user's portfolio, and the profit or loss
from the initial deposit.
The system should be able to report the holdings of the user at any point in time.
The system should be able to report the profit or loss of the user at any point in time.
The system should be able to list the transactions that the user has made over time.
The system should prevent the user from withdrawing funds that would leave them with a
negative balance, or from buying more shares than they can afford, or selling shares they
don't have.
The system has access to a function get_share_price(symbol) which returns the current price
of a share, and includes a test implementation that returns fixed prices for AAPL, TSLA, GOOGL.
""".strip()

_DEFAULT_MODULE_NAME = "accounts.py"
_DEFAULT_CLASS_NAME = "Account"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agentic_dev_crew.main",
        description=(
            "Agentic Dev Crew — orchestrates a 5-agent AI pipeline to produce "
            "a complete Python module from plain-English requirements."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    req_group = parser.add_mutually_exclusive_group()
    req_group.add_argument(
        "--requirements",
        metavar="TEXT",
        help="Requirements as an inline string.",
    )
    req_group.add_argument(
        "--requirements-file",
        metavar="PATH",
        help="Path to a .txt file containing the requirements.",
    )
    parser.add_argument(
        "--module-name",
        default=_DEFAULT_MODULE_NAME,
        metavar="FILENAME",
        help=f"Name of the Python module to generate (default: {_DEFAULT_MODULE_NAME}).",
    )
    parser.add_argument(
        "--class-name",
        default=_DEFAULT_CLASS_NAME,
        metavar="CLASSNAME",
        help=f"Name of the primary class in the module (default: {_DEFAULT_CLASS_NAME}).",
    )
    return parser


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run() -> None:
    """Parse CLI arguments and kick off the crew."""
    load_dotenv()

    parser = _build_parser()
    args = parser.parse_args()

    # Resolve requirements text
    if args.requirements_file:
        req_path = Path(args.requirements_file)
        if not req_path.exists():
            parser.error(f"Requirements file not found: {req_path}")
        requirements = req_path.read_text(encoding="utf-8").strip()
    elif args.requirements:
        requirements = args.requirements.strip()
    else:
        requirements = _DEFAULT_REQUIREMENTS

    module_name: str = args.module_name
    class_name: str = args.class_name

    inputs = {
        "requirements": requirements,
        "module_name": module_name,
        "class_name": class_name,
    }

    _print_run_header(module_name, class_name)

    result = AgenticDevCrew().crew().kickoff(inputs=inputs)

    # Post-process: strip markdown fences + write run_summary.md
    postprocess_outputs(module_name)

    print("\n" + "=" * 60)
    print("CREW COMPLETE — outputs written to output/")
    print("=" * 60)
    print(result.raw)


def _print_run_header(module_name: str, class_name: str) -> None:
    sep = "=" * 60
    print(f"\n{sep}")
    print("  Agentic Dev Crew")
    print(sep)
    print(f"  Module : {module_name}")
    print(f"  Class  : {class_name}")
    print(f"\n  Outputs (written to output/):")
    print(f"    {module_name}_design.md  — technical design document")
    print(f"    {module_name}            — Python implementation")
    print(f"    app.py                   — Gradio demo UI")
    print(f"    test_{module_name}       — unit test suite")
    print(f"    {module_name}_review.md  — staff engineer code review")
    print(f"    run_summary.md           — run audit trail")
    print(f"{sep}\n")


if __name__ == "__main__":
    run()
