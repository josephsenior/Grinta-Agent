import json
import re

IN_FILE = "output.jsonl"
OUT_FILE = "patch.jsonl"


def main():
    with open(IN_FILE, "r", encoding="utf-8") as fin:
        with open(OUT_FILE, "w", encoding="utf-8") as fout:
            for line in fin:
                data = json.loads(line)
                groups = re.match("(.*)__(.*)-(.*)", data["instance_id"])
                patch = {
                    "org": groups[1],
                    "repo": groups[2],
                    "number": groups[3],
                    "fix_patch": data["test_result"]["git_patch"],
                }
                fout.write(json.dumps(patch) + "\n")


if __name__ == "__main__":
    main()
