import argparse
import json
import logging
import unidiff
from evaluation.benchmarks.swe_bench.resource.swt_bench_constants import (
    MAP_VERSION_TO_INSTALL,
)

_LOGGER = logging.getLogger(__name__)


def remove_setup_files(model_patch: str, instance: dict, delete_setup_changes: bool):
    """Discard all changes that a patch applies to files changes by the pre_install script and that are reproduction scripts (top-level script)."""
    relevant_files = _get_relevant_setup_files(instance, delete_setup_changes)
    patch = _parse_patch_with_retry(model_patch)
    _remove_irrelevant_files(patch, relevant_files)
    return str(patch)


def _get_relevant_setup_files(instance: dict, delete_setup_changes: bool) -> list[str]:
    """Get list of relevant setup files to remove."""
    if not delete_setup_changes:
        return []

    setup_files = ["setup.py", "tox.ini", "pyproject.toml"]
    pre_install = (
        MAP_VERSION_TO_INSTALL.get(instance["repo"], {})
        .get(instance["version"], {})
        .get("pre_install", [])
    )
    return [
        file
        for file in setup_files
        if any((file in install and "sed" in install for install in pre_install))
    ]


def _parse_patch_with_retry(model_patch: str) -> unidiff.PatchSet:
    """Parse patch with retry mechanism for malformed patches."""
    for i in range(10):
        try:
            return unidiff.PatchSet(model_patch + i * "\n")
        except unidiff.UnidiffParseError:
            pass
    raise ValueError("Failed to parse patch after 10 attempts")


def _remove_irrelevant_files(
    patch: unidiff.PatchSet, relevant_files: list[str]
) -> None:
    """Remove files that should be excluded from the patch."""
    to_delete = [
        i for i, file in enumerate(patch) if _should_delete_file(file, relevant_files)
    ]
    for i in reversed(to_delete):
        del patch[i]


def _should_delete_file(file, relevant_files: list[str]) -> bool:
    """Check if a file should be deleted from the patch."""
    return (
        any(f in file.source_file for f in relevant_files)
        or file.target_file.count("/") == 1
    )


def main(prediction_file: str):
    """Main function to extract the model patches from the Forge prediction file and turn them into the expected SWT-Bench format."""
    with open(prediction_file, encoding="utf-8") as f:
        for line in f:
            pred = json.loads(line)
            try:
                git_diff = pred["test_result"]["git_patch"]
            except KeyError:
                _LOGGER.warning(
                    "Warning: No git diff found for instance %s", pred["instance_id"]
                )
                continue
            ci_mode = pred["metadata"]["details"].get("mode", "") == "swt-ci"
            try:
                git_diff = remove_setup_files(git_diff, pred["instance"], ci_mode)
            except Exception:
                _LOGGER.warning(
                    "Warning: Invalid git diff found for instance %s",
                    pred["instance_id"],
                )
            print(
                json.dumps(
                    {
                        "instance_id": pred["instance_id"],
                        "model_name_or_path": f"{
                            pred['metadata']['llm_config']['openrouter_app_name']
                        }__{pred['metadata']['agent_class']}__{
                            pred['metadata']['llm_config']['model']
                        }",
                        "model_patch": git_diff,
                        "full_output": json.dumps(pred),
                    }
                )
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prediction_file",
        type=str,
        required=True,
        help="Path to the prediction file (.../outputs.jsonl)",
    )
    args = parser.parse_args()
    main(args.prediction_file)
