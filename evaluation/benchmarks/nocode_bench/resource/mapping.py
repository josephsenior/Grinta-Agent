"""Mapping instance_id to resource_factor.

Different instances may have different resource requirements.
e.g., some instances may require more memory/CPU to run inference.
This file tracks the resource requirements of different instances.
"""

import json
import os
from forge.core.logger import forge_logger as logger

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RUNTIME_RESOURCE_FACTOR = int(
    os.environ.get("DEFAULT_RUNTIME_RESOURCE_FACTOR", 1)
)
_global_resource_mapping: dict[str, dict[str, float]] = {}


def get_resource_mapping(dataset_name: str) -> dict[str, float]:
    if dataset_name not in _global_resource_mapping:
        file_path = os.path.join(CUR_DIR, f"{dataset_name}.json")
        if not os.path.exists(file_path):
            logger.info("Resource mapping for %s not found.", dataset_name)
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            _global_resource_mapping[dataset_name] = json.load(f)
        logger.debug("Loaded resource mapping for %s", dataset_name)
    return _global_resource_mapping[dataset_name]


def get_instance_resource_factor(dataset_name: str, instance_id: str) -> int:
    resource_mapping = get_resource_mapping(dataset_name)
    if resource_mapping is None:
        return DEFAULT_RUNTIME_RESOURCE_FACTOR
    return int(resource_mapping.get(instance_id, DEFAULT_RUNTIME_RESOURCE_FACTOR))
