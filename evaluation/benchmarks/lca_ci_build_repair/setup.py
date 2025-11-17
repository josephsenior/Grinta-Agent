"""Installs LCA CI Build Repair benchmark with scripts for OH integration."""

import os
import shutil
import subprocess
import yaml


def setup():
    print("Reading config.yaml")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    lca_path = config["LCA_PATH"]
    lca_ci_path = os.path.join(
        lca_path, "lca-baselines", "ci-builds-repair", "ci-builds-repair-benchmark"
    )
    repo_url = "https://github.com/juanmichelini/lca-baselines"
    print(f"Cloning lca-baselines repository from {repo_url} into {lca_path}")
    result = subprocess.run(
        ["git", "clone", repo_url], cwd=lca_path, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Warning cloning repository: {result.stderr}")
    print("Switching branches")
    result = subprocess.run(
        ["git", "switch", "open-hands-integration"],
        cwd=lca_ci_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Warning switching repository: {result.stderr}")
    lca_ci_config_path = os.path.join(lca_ci_path, "config.yaml")
    print(f"Copying config.yaml to {lca_ci_config_path}")
    shutil.copy(config_path, lca_ci_config_path)
    print(f"Running 'poetry install' in {lca_ci_path}")
    result = subprocess.run(
        ["poetry", "install"], cwd=lca_ci_path, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Warning during poetry install: {result.stderr}")


if __name__ == "__main__":
    setup()
