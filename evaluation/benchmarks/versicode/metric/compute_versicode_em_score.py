"""Calculate the cdc score for line and block."""

import ast
import json
import math
import os
import re


def is_code_valid(code):
    try:
        compile(code, "<string>", "exec")
        return True
    except Exception:
        return False


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
    correct_match = re.search(pattern, correct_code)
    if not correct_match:
        return False

    correct_params = correct_match[1].strip()
    correct_param_list = [p.strip() for p in correct_params.split(",") if p.strip()]

    test_match = re.search(pattern, test_code)
    if not test_match:
        return False

    test_params = test_match[1].strip()
    test_param_list = [p.strip() for p in test_params.split(",") if p.strip()]

    return _validate_keyword_parameters(correct_param_list, test_param_list)


def _validate_keyword_parameters(
    correct_param_list: list[str], test_param_list: list[str]
) -> bool:
    """Validate that keyword parameters are correctly used."""
    for correct_param in correct_param_list:
        if "=" in correct_param:
            param_name = correct_param.split("=")[0].strip()
            if not _has_keyword_parameter(test_param_list, param_name):
                return False
    return True


def _has_keyword_parameter(test_param_list: list[str], param_name: str) -> bool:
    """Check if a keyword parameter exists in the test parameter list."""
    return any(
        param_name in test_param and "=" in test_param for test_param in test_param_list
    )


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


def compute_line_score_k(
    answer: str, model_output: list, k: int, model_filled_code, core_line
):
    n = len(model_output)
    c = sum(
        (bool(re.search(f"\\b{re.escape(answer)}\\b", code)) for code in model_output)
    )
    return 1.0 if n - c < k else 1 - math.comb(n - c, k) / math.comb(n, k)


def compute_block_score_k(
    answer: str,
    model_output: list,
    k: int,
    model_filled_code,
    core_line_in_core_block,
    core_line_in_output_clear,
):
    n = len(model_output)
    c = sum(
        (bool(re.search(f"\\b{re.escape(answer)}\\b", code)) for code in model_output)
    )
    return 1.0 if n - c < k else 1 - math.comb(n - c, k) / math.comb(n, k)


def compute_score_k(answer: str, model_output: list, k: int):
    n = len(model_output)
    c = sum(
        (
            bool(re.search(f"\\b{re.escape(answer)}\\b", code) and is_code_valid(code))
            for code in model_output
        )
    )
    return 1.0 if n - c < k else 1 - math.comb(n - c, k) / math.comb(n, k)


k = 3
task = "block"
json_name = f"Versicode_{task}_completion.json"
folder_path = f"../data/result_data/{task}_completion"
model_list = os.listdir(folder_path)
for model in model_list:
    model_json_path = os.path.join(folder_path, model, json_name)
    with open(model_json_path, "r", encoding="utf-8") as fr:
        lodict = json.load(fr)
    data_list = lodict
    score_list = []
    for data in data_list:
        answer = data["core_token"]
        model_output = ast.literal_eval(data["model_output_clear"])  # nosec B307
        if task == "line":
            model_filled_code = [
                data["masked_code"].replace("<mask>", i) for i in model_output
            ]
            core_line = data["core_line"]
            score_list.append(
                compute_line_score_k(
                    answer, model_output, k, model_filled_code, core_line
                )
            )
        else:
            model_filled_code = ast.literal_eval(data["model_output_clear"])  # nosec B307
            core_line = data["core_line"]
            core_line_in_output_clear = data["core_line_in_output_clear"]
            score_list.append(
                compute_block_score_k(
                    answer,
                    model_output,
                    k,
                    model_filled_code,
                    core_line,
                    core_line_in_output_clear,
                )
            )
    final_score = sum(score_list) / len(score_list)
    print(f"{model}, {task} completion task, em@{k} score: {final_score}")
