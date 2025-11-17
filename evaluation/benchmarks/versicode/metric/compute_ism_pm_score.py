"""评测block的预测能力.

1、判断是否包含正确的函数名
2、判断是否合法
3、计算ISM，和PM.
"""

import ast
import io
import json
import math
import os
import re
import tokenize


def is_code_valid(code):
    try:
        compile(code, "<string>", "exec")
        return True
    except Exception:
        return False


def longest_common_prefix_between_lists_with_elements(list1, list2):
    """Compute the longest common prefix length between elements of two string lists.

    :param list1:
    :param list2:
    :return:
    """
    max_prefix_length = 0
    max_prefix_elements = ()
    for str1 in list1:
        for str2 in list2:
            prefix_length = 0
            min_len = min(len(str1), len(str2))
            for i in range(min_len):
                if str1[i] == str2[i]:
                    prefix_length += 1
                else:
                    break
            if prefix_length > max_prefix_length:
                max_prefix_length = prefix_length
                max_prefix_elements = (str1, str2)
    return (max_prefix_length, max_prefix_elements)


def _tokenize_code_safely(code: str) -> tuple[list, bool]:
    """Safely tokenize code and return tokens with success flag."""
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline))
        return tokens, True
    except Exception:
        return code.splitlines(), False


def _extract_identifiers_from_tokens(tokens: list, is_tokenized: bool) -> list:
    """Extract identifiers from tokens."""
    if not is_tokenized:
        return tokens

    try:
        return [token.string for token in tokens if token.type == tokenize.NAME]
    except Exception:
        return tokens


def _extract_identifiers_from_tokenized_output(tokens: list) -> list:
    """Extract identifiers from tokenized output tokens."""
    try:
        return [token.string for token in tokens if token.type == tokenize.NAME]
    except Exception:
        return tokens


def get_token(ans_code: str, output_code: str):
    """Tokenize code into identifiers and return two identifier lists.

    :param ans_code:
    :param output_code:
    :return:
    """
    tokens_ans, ans_flag = _tokenize_code_safely(ans_code)
    tokens_output, output_flag = _tokenize_code_safely(output_code)

    identifiers_ans = _extract_identifiers_from_tokens(tokens_ans, ans_flag)
    identifiers_output = (
        _extract_identifiers_from_tokenized_output(tokens_output)
        if output_flag
        else tokens_output
    )

    return (identifiers_ans, identifiers_output)


def get_token_per_line(code: str):
    """对每一行代码进行词法分析，记录每一行的标识符.

    :param code: 代码字符串
    :return: 每一行的标识符列表组成的列表.
    """
    lines = code.split("\n")
    identifiers_per_line = []
    for line in lines:
        tokens = tokenize.tokenize(io.BytesIO(line.encode("utf-8")).readline)
        identifiers = []
        try:
            identifiers.extend(
                (token.string for token in tokens if token.type == tokenize.NAME)
            )
        except Exception:
            identifiers = line.split(" ")
        identifiers_per_line.append(identifiers)
    return identifiers_per_line


def get_ISM(answer_code: str, model_output_list: list, answer_name: str) -> list:
    """Compute ISM and return an ordered list of scores.

    :return:
    """
    score_list = []
    for code in model_output_list:
        if "```python" in code:
            code = code.replace("```python", "")
            code = code.replace("```", "")
        if not re.search(f"\\b{re.escape(answer_name)}\\b", code) or not is_code_valid(
            code
        ):
            score_list.append(0)
            continue
        identifiers_ans, identifiers_output = get_token(answer_code, code)
        max_len, elements = longest_common_prefix_between_lists_with_elements(
            identifiers_ans, identifiers_output
        )
        if max_len != 0:
            base_element_len = max(len(elements[0]), len(elements[1]))
            temp_score = max_len / base_element_len
            score_list.append(temp_score)
        else:
            score_list.append(0)
    return sorted(score_list, reverse=True)


def get_ISM_without_verification(
    answer_code: str, model_output_list: list, answer_name: str
) -> list:
    """Compute ISM without verification and return an ordered list of scores.

    :return:
    """
    score_list = []
    for code in model_output_list:
        if answer_name not in code:
            score_list.append(0)
            continue
        identifiers_ans, identifiers_output = get_token(answer_code, code)
        max_len, elements = longest_common_prefix_between_lists_with_elements(
            identifiers_ans, identifiers_output
        )
        if max_len != 0:
            base_element_len = max(len(elements[0]), len(elements[1]))
            temp_score = max_len / base_element_len
            score_list.append(temp_score)
        else:
            score_list.append(0)
    return sorted(score_list, reverse=True)


def longest_common_prefix_with_lengths(list1, list2):
    """Compute the longest prefix matches across two 2D lists and return lengths.

    :param list1: 第一个二维列表
    :param list2: 第二个二维列表
    :return: 最长前缀匹配长度以及拥有最长前缀匹配长度的两个子列表的长度.
    """
    max_length = 0
    len_list1 = 0
    len_list2 = 0
    for sublist1 in list1:
        for j, sublist2 in enumerate(list2):
            match_length = 0
            min_length = min(len(sublist1), len(sublist2))
            for k in range(min_length):
                if sublist1[k] == sublist2[k]:
                    match_length += 1
                else:
                    break
            if match_length > max_length:
                max_length = match_length
                len_list1 = len(sublist1)
                len_list2 = len(sublist2)
    return (max_length, len_list1, len_list2)


def get_PM(answer_code: str, model_output_list: list, answer_name: str) -> list:
    """Compute PM and return an ordered list of scores.

    :return:
    """
    score_list = []
    for code in model_output_list:
        if "```python" in code:
            code = code.replace("```python", "")
            code = code.replace("```", "")
        if not re.search(f"\\b{re.escape(answer_name)}\\b", code) or not is_code_valid(
            code
        ):
            score_list.append(0)
            continue
        ans_list = get_token_per_line(answer_code)
        output_token_list = get_token_per_line(code)
        max_len, len1, len2 = longest_common_prefix_with_lengths(
            ans_list, output_token_list
        )
        base_element_len = max(len1, len2)
        if base_element_len != 0:
            temp_score = max_len / base_element_len
            score_list.append(temp_score)
        else:
            score_list.append(0)
    return sorted(score_list, reverse=True)


def get_score(score_list: list, k):
    """Compute score@n,k.

    :param score_list:
    :param k:
    :return:
    """
    n = len(score_list)
    sum = 0
    final = n - k + 1
    for i in range(1, final + 1):
        sum += math.comb(n - i, k - 1) * score_list[i - 1]
    return sum / math.comb(n, k)


k = 1
task = "block"
json_name = f"Versicode_{task}_completion.json"
folder_path = f"../data/result_data/{task}_completion"
model_list = os.listdir(folder_path)
for model in model_list:
    model_json_path = os.path.join(folder_path, model, json_name)
    with open(model_json_path, "r", encoding="utf-8") as fr:
        lodict = json.load(fr)
    data_dict = lodict
    data_list = data_dict
    data_len = len(data_list)
    sum_ISM = 0
    sum_PM = 0
    for data in data_list:
        model_output_list = ast.literal_eval(data["model_output_clear"])[:1]  # nosec B307
        temp_list = []
        for o in model_output_list:
            temp_out = o.replace("```python", "")
            temp_out = temp_out.replace("```", "")
            temp_list.append(temp_out)
        model_output_list = temp_list
        answer_code = data["code"]
        answer_name = data["core_token"]
        ISM_score_list = get_ISM(answer_code, model_output_list, answer_name)
        PM_score_list = get_PM(answer_code, model_output_list, answer_name)
        ISM_score = get_score(ISM_score_list, k)
        PM_score = get_score(PM_score_list, k)
        sum_ISM += ISM_score
        sum_PM += PM_score
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        "%s, %s completion task, ISM@%d score: %s", model, task, k, sum_ISM / data_len
    )
    logger.info(
        "%s, %s completion task, PM@%d score: %s", model, task, k, sum_PM / data_len
    )
