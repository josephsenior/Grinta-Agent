import json
from pathlib import Path
from typing import cast
from datasets import Dataset, load_dataset
from evaluation.benchmarks.testgeneval.constants import KEY_INSTANCE_ID, TestGenEvalInstance


def get_test_directives(instance: TestGenEvalInstance) -> list:
    """Get test directives from the test_patch of a task instance.

    Args:
        instance (dict): task instance
    Returns:
        directives (list): List of test directives
    """
    if instance["repo"] == "swe-bench/humaneval":
        return ["test.py"]
    directives = [f"/testbed/{instance['test_file']}"]
    if instance["repo"] == "django/django":
        directives = [instance["test_file"]]
        directives_transformed = []
        for d in directives:
            d = d[: -len(".py")] if d.endswith(".py") else d
            d = d[len("tests/"):] if d.startswith("tests/") else d
            d = d.replace("/", ".")
            directives_transformed.append(d)
        directives = directives_transformed
    return directives


def load_testgeneval_dataset(name="kjain14/testgeneval", split="test", ids=None) -> list[TestGenEvalInstance]:
    """Load SWE-bench dataset from Hugging Face Datasets or local .json/.jsonl file."""
    if ids:
        ids = set(ids)

    dataset, dataset_ids = _load_dataset_from_source(name, split)

    if ids:
        _validate_and_filter_dataset(dataset, ids, dataset_ids)

    return [cast(TestGenEvalInstance, instance) for instance in dataset]


def _load_dataset_from_source(name: str, split: str) -> tuple[list, set[str]]:
    """Load dataset from file or Hugging Face."""
    if name.endswith(".json") or name.endswith(".jsonl"):
        return _load_from_local_file(name)
    else:
        return _load_from_huggingface(name, split)


def _load_from_local_file(name: str) -> tuple[list, set[str]]:
    """Load dataset from local JSON/JSONL file."""
    dataset = json.loads(Path(name).read_text())
    dataset_ids = {instance[KEY_INSTANCE_ID] for instance in dataset}
    return dataset, dataset_ids


def _load_from_huggingface(name: str, split: str) -> tuple[list, set[str]]:
    """Load dataset from Hugging Face."""
    name = _normalize_dataset_name(name)
    dataset = cast(Dataset, load_dataset(name, split=split))  # nosec B615 - Safe: evaluation benchmark dataset
    dataset_ids = {instance["id"] for instance in dataset}
    return dataset, dataset_ids


def _normalize_dataset_name(name: str) -> str:
    """Normalize dataset name to Hugging Face format."""
    if name.lower() in {"testgeneval"}:
        return "kjain14/testgeneval"
    elif name.lower() in {"testgeneval-lite", "testgenevallite", "lite"}:
        return "kjain14/testgenevallite"
    return name


def _validate_and_filter_dataset(dataset: list, ids: set[str], dataset_ids: set[str]) -> None:
    """Validate and filter dataset by IDs."""
    if ids - dataset_ids:
        raise ValueError(f"Some instance IDs not found in dataset!\nMissing IDs:\n{' '.join(ids - dataset_ids)}")

    # Filter dataset in place
    dataset[:] = [instance for instance in dataset if instance["id"] in ids]
