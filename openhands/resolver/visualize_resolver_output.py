from __future__ import annotations

import argparse
import json as _json
import logging
from pathlib import Path

from openhands.resolver.io_utils import load_single_resolver_output

try:
    from openhands.core.pydantic_compat import model_dump_json, model_dump_with_options
except Exception:
    model_dump_with_options = None
    model_dump_json = None
try:
    from openhands.core.io import print_json_stdout
except Exception:
    print_json_stdout = None
logger = logging.getLogger(__name__)


def _try_model_dump_with_options(resolver_output) -> dict | None:
    """Try to serialize using model_dump_with_options."""
    if model_dump_with_options is None:
        return None

    try:
        return model_dump_with_options(resolver_output)
    except Exception:
        logger.debug("model_dump_with_options raised; will try JSON string fallback", exc_info=True)
        return None


def _try_model_dump_json(resolver_output) -> dict | None:
    """Try to serialize using model_dump_json."""
    if model_dump_json is None:
        return None

    try:
        json_str = model_dump_json(resolver_output)
        return _json.loads(json_str)
    except Exception:
        logger.debug("model_dump_json -> json.loads fallback failed", exc_info=True)
        return None


def _print_with_fallback(resolver_output) -> None:
    """Print resolver output with multiple fallback strategies."""
    if model_dump_json is not None:
        try:
            json_str = model_dump_json(resolver_output)
            parsed = _json.loads(json_str) if json_str else None

            if parsed is not None and print_json_stdout is not None:
                try:
                    print_json_stdout(parsed, pretty=True)
                    return
                except Exception:
                    logger.exception("print_json_stdout failed in model_dump_json fallback; printing raw JSON string")

            return
        except Exception:
            logger.exception("model_dump_json fallback printing failed; falling back to repr")


def _print_obj(obj: dict) -> None:
    """Print object using best available method."""
    if print_json_stdout is not None:
        try:
            print_json_stdout(obj, pretty=True)
        except Exception:
            logger.exception("print_json_stdout failed; falling back to json.dumps()")
    else:
        pass


def visualize_resolver_output(issue_number: int, output_dir: str, vis_method: str) -> None:
    output_jsonl = Path(output_dir) / "output.jsonl"
    resolver_output = load_single_resolver_output(str(output_jsonl), issue_number)

    if vis_method != "json":
        msg = f"Invalid visualization method: {vis_method}"
        raise ValueError(msg)

    # Try primary serialization methods
    obj = _try_model_dump_with_options(resolver_output)
    if obj is None:
        obj = _try_model_dump_json(resolver_output)

    # Print result
    if obj is None:
        _print_with_fallback(resolver_output)
    else:
        _print_obj(obj)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize a patch.")
    parser.add_argument("--issue-number", type=int, required=True, help="Issue number to send the pull request for.")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory to write the results.")
    parser.add_argument(
        "--vis-method",
        type=str,
        default="json",
        choices=["json"],
        help="Method to visualize the patch [json].",
    )
    my_args = parser.parse_args()
    visualize_resolver_output(
        issue_number=my_args.issue_number,
        output_dir=my_args.output_dir,
        vis_method=my_args.vis_method,
    )
