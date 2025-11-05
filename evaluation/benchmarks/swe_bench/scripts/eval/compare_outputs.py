import argparse
import logging
import os
import subprocess
import pandas as pd
from termcolor import colored

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser(description="Compare two swe_bench output JSONL files and print the resolved diff")
parser.add_argument("input_file_1", type=str)
parser.add_argument("input_file_2", type=str)
parser.add_argument("--show-paths", action="store_true", help="Show visualization paths for failed instances")
parser.add_argument("--only-x-instances", action="store_true", help="Only show instances that are ran by X")
args = parser.parse_args()
df1 = pd.read_json(args.input_file_1, orient="records", lines=True)
df2 = pd.read_json(args.input_file_2, orient="records", lines=True)
if args.only_x_instances:
    instance_ids_1 = set(df1["instance_id"].tolist())
    logger.info("Before removing instances not in X=%s: Y=%d instances", args.input_file_1, df2.shape[0])
    df2 = df2[df2["instance_id"].isin(instance_ids_1)]
    logger.info("After removing instances not in X=%s: Y=%d instances", args.input_file_1, df2.shape[0])


def summarize_file(file_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    summarize_script = os.path.join(script_dir, "summarize_outputs.py")
    logger.info("\nSummary for %s:", file_path)
    logger.info("=" * 80)
    subprocess.run(["python", summarize_script, file_path], check=True)
    logger.info("=" * 80)


summarize_file(args.input_file_1)
summarize_file(args.input_file_2)
df = pd.merge(df1, df2, on="instance_id", how="inner")


def _get_resolved(report):
    if report is None:
        return False
    return False if isinstance(report, float) else report.get("resolved", False)


df["resolved_x"] = df["report_x"].apply(_get_resolved)
df["resolved_y"] = df["report_y"].apply(_get_resolved)
df["diff"] = df.apply(lambda x: x["resolved_x"] != x["resolved_y"], axis=1)
df_diff = df[df["diff"]].sort_values(by=["resolved_x", "resolved_y"], ascending=[False, False])
df_diff = df_diff[df_diff["resolved_x"].notna() & df_diff["resolved_y"].notna()]
logger.info("X=%s", args.input_file_1)
logger.info("Y=%s", args.input_file_2)
logger.info("# diff=%d", df_diff.shape[0])
df_diff = df_diff[["instance_id", "resolved_x", "resolved_y", "report_x", "report_y"]]
logger.info("-" * 100)
df_diff_x_only = df_diff[df_diff["resolved_x"] & ~df_diff["resolved_y"]].sort_values(by="instance_id")
logger.info("# x resolved but y not=%d", df_diff_x_only.shape[0])
logger.info("\n%s", df_diff_x_only[["instance_id", "report_x", "report_y"]])
logger.info("-" * 100)
df_diff_y_only = df_diff[~df_diff["resolved_x"] & df_diff["resolved_y"]].sort_values(by="instance_id")
logger.info("# y resolved but x not=%d", df_diff_y_only.shape[0])
logger.info("\n%s", df_diff_y_only[["instance_id", "report_x", "report_y"]])
x_only_by_repo = {}
for instance_id in df_diff_x_only["instance_id"].tolist():
    repo = instance_id.split("__")[0]
    x_only_by_repo.setdefault(repo, []).append(instance_id)
y_only_by_repo = {}
for instance_id in df_diff_y_only["instance_id"].tolist():
    repo = instance_id.split("__")[0]
    y_only_by_repo.setdefault(repo, []).append(instance_id)
logger.info("-" * 100)
logger.info(colored("Repository comparison (x resolved vs y resolved):", "cyan", attrs=["bold"]))
all_repos = sorted(set(list(x_only_by_repo.keys()) + list(y_only_by_repo.keys())))
repo_diffs = []
for repo in all_repos:
    x_count = len(x_only_by_repo.get(repo, []))
    y_count = len(y_only_by_repo.get(repo, []))
    diff = y_count - x_count
    repo_diffs.append((repo, diff))
repo_diffs.sort(key=lambda x: (-x[1], x[0]))
threshold = max(3, sum((d[1] for d in repo_diffs)) / len(repo_diffs) * 1.5 if repo_diffs else 0)
x_input_file_folder = os.path.join(os.path.dirname(args.input_file_1), "output.viz")
for repo, diff in repo_diffs:
    x_instances = x_only_by_repo.get(repo, [])
    y_instances = y_only_by_repo.get(repo, [])
    is_significant = diff >= threshold
    repo_color = "red" if is_significant else "yellow"
    logger.info("\n%s:", colored(repo, repo_color, attrs=["bold"]))
    logger.info("%s", colored(f"Difference: {diff} instances! (Larger diff = Y better)", repo_color, attrs=["bold"]))
    logger.info(colored(f"X resolved but Y failed: ({len(x_instances)} instances)", "green"))
    if x_instances:
        logger.info("  %s", str(x_instances))
    logger.info(colored(f"Y resolved but X failed: ({len(y_instances)} instances)", "red"))
    if y_instances:
        logger.info("  %s", str(y_instances))
        if args.show_paths:
            logger.info(colored("    Visualization path for X failed:", "cyan", attrs=["bold"]))
            for instance_id in y_instances:
                instance_file = os.path.join(x_input_file_folder, f"false.{instance_id}.md")
                logger.info("    %s", instance_file)
