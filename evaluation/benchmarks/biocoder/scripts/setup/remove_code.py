import argparse
import os
import re
from collections import defaultdict


def get_likely_indent_size(array_of_tabs) -> int:
    sizes = defaultdict(int)
    for i in range(len(array_of_tabs) - 1):
        diff = array_of_tabs[i + 1] - array_of_tabs[i]
        if diff > 0:
            sizes[diff] += 1
    return int(max(sizes, key=sizes.get)) if sizes else 4


def get_target_filepath(self):
    return os.path.join(
        self.workspace_mount_path, self.biocoder_instance.repository.split("/")[1], self.biocoder_instance.filePath
    )


def remove_code(target_filepath: str, line_start: int, line_end: int, language: str):
    comment_prefix = {"python": "#", "java": "//"}
    with open(target_filepath, "r", encoding='utf-8') as f:
        lines = f.read().split("\n")
        signature_line = lines[line_start - 1]

        def get_indent_size(s: str):
            return len(re.match("\\s*", s).group())

        indent_sizes = list(map(get_indent_size, lines))
        indent_size = get_likely_indent_size(indent_sizes)
        comment_indent_size = get_indent_size(signature_line) + indent_size
        lines = (
            lines[:line_start]
            + [f"{' ' * comment_indent_size + comment_prefix[language.lower()]}TODO: replace with your code here"]
            + [""] * 2
            + lines[line_end:]
        )
    first_line_after_removed_index = line_start
    while len(lines[first_line_after_removed_index].strip()) == 0 and first_line_after_removed_index < len(lines):
        first_line_after_removed_index += 1
    first_line_after_removed = lines[first_line_after_removed_index]
    print("FIRST LINE AFTER REMOVED: ", first_line_after_removed)
    with open("/testing_files/first_line_after_removed.txt", "w", encoding='utf-8') as f:
        f.write(first_line_after_removed)
    with open(target_filepath, "w", encoding='utf-8') as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_filepath", type=str, required=True)
    parser.add_argument("--line_start", type=int, required=True)
    parser.add_argument("--line_end", type=int, required=True)
    parser.add_argument("--language", type=str, required=True)
    args = parser.parse_args()
    remove_code(args.target_filepath, args.line_start, args.line_end, args.language)
