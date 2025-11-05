"""Calculate the cdc score for migration."""

import json
import math
import os
import re


def is_correct_parameter_count(function_name, correct_code, test_code):
    """Check whether the parameter counts match.

    :param function_name:
    :param correct_code:
    :param test_code:
    :return:
    """
    pattern = f"{function_name}\\((.*?)\\)"
    if correct_match := re.search(pattern, correct_code):
        correct_params = correct_match[1].strip()
        correct_param_list = [p.strip() for p in correct_params.split(",") if p.strip()]
        expected_count = len(correct_param_list)
    else:
        expected_count = 0
    if not (test_match := re.search(pattern, test_code)):
        return expected_count == 0 and function_name in test_code
    test_params = test_match[1].strip()
    test_param_list = [p.strip() for p in test_params.split(",") if p.strip()]
    return len(test_param_list) == expected_count


def check_keyword_parameters(function_name, correct_code, test_code):
    """Check whether keyword parameters are used correctly.

    :param function_name:
    :param correct_code:
    :param test_code:
    :return:
    """
    pattern = f"{function_name}\\((.*?)\\)"
    if correct_match := re.search(pattern, correct_code):
        correct_params = correct_match[1].strip()
        correct_param_list = [p.strip() for p in correct_params.split(",") if p.strip()]
        if test_match := re.search(pattern, test_code):
            test_params = test_match[1].strip()
            test_param_list = [p.strip() for p in test_params.split(",") if p.strip()]
            for correct_param in correct_param_list:
                if "=" in correct_param:
                    param_name = correct_param.split("=")[0].strip()
                    if not any((param_name in test_param and "=" in test_param for test_param in test_param_list)):
                        return False
            return True
    return False


def with_correct(answer_code: str, model_output: str) -> bool:
    """When the answer uses a with block, check if the model output also uses a with block.

    :param answer_code:
    :param model_output:
    :return:
    """
    if not answer_code.startswith("with") and (not model_output.startswith("with")):
        return True
    elif answer_code.startswith("with") and model_output.startswith("with"):
        return True
    else:
        return False


def compute_block_score_k(
    answer: str, model_output: list, k: int, model_filled_code, core_line_in_core_block, core_line_in_output_clear
):
    """cdc需要满足五个条件，em只需要满足第一个条件."""
    n = len(model_output)
    c = sum(
        (
            bool(
                re.search(
                    f"\\b{
                        re.escape(answer)}\\b",
                    code,
                )
                and is_code_valid(model_filled_code[index])
                and is_correct_parameter_count(answer, core_line_in_core_block, core_line_in_output_clear[index])
                and with_correct(core_line_in_core_block, core_line_in_output_clear[index])
                and check_keyword_parameters(answer, core_line_in_core_block, core_line_in_output_clear[index])
            )
            for index, code in enumerate(model_output)
        )
    )
    return 1.0 if n - c < k else 1 - math.comb(n - c, k) / math.comb(n, k)


def is_code_valid(code):
    try:
        compile(code, "<string>", "exec")
        return True
    except Exception:
        return False


def compute_score_k(answer: str, model_output: list, k: int):
    c = 0
    n = len(model_output)
    for output in model_output:
        if "```python" in output:
            output = output.replace("```python", "")
            output = output.replace("```", "")
        if re.search(f"\\b{re.escape(answer)}\\b", output) and is_code_valid(output):
            c += 1
    return 1.0 if n - c < k else 1 - math.comb(n - c, k) / math.comb(n, k)


k = 1
json_name = "VersiCode_migration.json"
task = "migration"
folder_path = "../data/result_data/code_migration"
model_list = os.listdir(folder_path)
for model in model_list:
    model_json_path = os.path.join(folder_path, model, json_name)
    with open(model_json_path, "r", encoding="utf-8") as fr:
        lodict = json.load(fr)
    data_list = lodict
    score_list = []
    for data in data_list:
        answer = data["new_name"]
        model_output = data["model_output_clear"]
        model_filled_code = model_output
        core_line_in_core_block = data["core_line_in_code"]
        core_line_in_output_clear = data["core_line_in_output_clear"]
        score_list.append(
            compute_block_score_k(
                answer, model_filled_code, k, model_filled_code, core_line_in_core_block, core_line_in_output_clear
            )
        )
    final_score = sum(score_list) / len(score_list)
    print(f"{model}, {task} task, cdc@{k} score: {final_score}")
