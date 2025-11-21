import ast
import logging
import re
import traceback
from typing import Any
import numpy as np
from sympy import Rational
from tasks.base import Task

LOGGER = logging.getLogger("MINT")


class ReasoningTask(Task):
    task_name = "reasoning"

    def __init__(self, id: str, prompt: str, reference: str, **kwargs):
        super().__init__(**kwargs)
        self._id = id
        self._prompt = prompt.strip()
        self._reference = reference.strip().lower()

    def extract_answer(self, solution: str) -> str | None:
        """Extract the answer from the given solution."""
        return solution.lower().strip()

    def compare_w_digits(self, reference: str, answer: str) -> bool:
        """Compare the reference and answer with digits."""
        try:
            float(reference)
            float(answer)
            return abs(float(reference) - float(answer)) <= 0.05 * abs(float(reference))
        except ValueError:
            return reference in answer
        except Exception as e:
            raise ValueError(f"Cannot compare {reference} and {answer}") from e

    def success(self, solution: str) -> bool:
        answer = self.extract_answer(solution)
        return self.compare_w_digits(self._reference, answer)


class MultipleChoiceTask(Task):
    """Subclass of Task for multiple choice tasks."""

    task_name = "reasoning"

    def __init__(self, id, prompt: str, reference: str, **kwargs):
        super().__init__(**kwargs)
        self._id = id
        self.hide_options = kwargs.get("hide_options", False)
        if self.hide_options:
            self._prompt = prompt.split("Options:")[0].strip()
        else:
            self._prompt = prompt
        self._reference = reference.strip().lower()
        self._options = self.extract_options(prompt)
        try:
            for option in self._options.values():
                float(option)
            self.hide_options = True
        except ValueError:
            pass
        self.metadata.update({"options": self._options})

    def extract_answer(self, solution: str) -> str | None:
        solution = solution.lower().strip()
        for letter in "abcdefghijklmnopqrstuvwxyz":
            if f"{letter})" in solution or f"{letter} )" in solution:
                print("SOLUTION", letter)
                return letter
            else:
                print("SOLUTION", solution)
                return solution

    def compare_w_digits(self, reference: str, answer: str) -> bool:
        if reference.isdigit() and answer.isdigit():
            return abs(float(reference) - float(answer)) <= 0.05 * float(reference)
        else:
            return reference in answer

    def success(self, solution: str) -> bool:
        answer = self.extract_answer(solution)
        if self.compare_w_digits(self._reference, answer):
            return True
        correct_option = self._options[self._reference]
        wrong_option_list = list(self._options.values())
        print("OPTIONS", correct_option, wrong_option_list)
        print("ANSWER", answer)
        for i in wrong_option_list:
            if i in correct_option:
                wrong_option_list.remove(i)
        for i in wrong_option_list:
            if self.compare_w_digits(i, answer) or i in answer:
                return False
        return bool(
            self.compare_w_digits(correct_option, answer) or correct_option in answer
        )

    def extract_options(self, prompt: str) -> dict:
        prompt = prompt.split("Options: ")[-1]
        options_match = prompt.split(" , ")
        options = {}
        for i in range(len(options_match)):
            option = options_match[i].strip("[]' ")
            option = option.split(")")
            letter = option[0].lower().strip()
            content = (
                option[1]
                .lower()
                .strip(".")
                .replace(". Which option is correct?", "")
                .replace(". Which one is correct?", "")
                .strip()
            )
            options[letter] = content
        return options


def compare_two_numbers(p, gt):
    if isinstance(p, (int, float)):
        pass
    elif isinstance(p, (bool, complex, dict, list, str, tuple)):
        return False
    else:
        raise ValueError(p)
    return within_eps(pred=p, gt=gt) if isinstance(gt, float) else round(p) == gt


def compare_two_list(pred, gt):
    if not isinstance(pred, list):
        return False
    elif len(pred) != len(gt):
        return False
    elif any((not isinstance(x, (int, float)) for x in pred)):
        return False
    else:
        pred = sorted(pred)
        gt = sorted(gt)
        return all((compare_two_numbers(p, g) for p, g in zip(pred, gt)))


def within_eps(pred: float, gt: float):
    eps = abs(gt) * 0.04
    return pred >= gt - eps and pred <= gt + eps


def parse_number_list(s: str):
    return ast.literal_eval(s)


def is_number(string):
    pattern = "^[-+]?(\\d{1,3}(,\\d{3})*|(\\d+))(\\.\\d+)?$"
    match = re.match(pattern, string)
    return bool(match)


def is_scientific_number(string):
    pattern = "^[-+]?\\d+(\\.\\d+)?e[-]?\\d+$"
    match = re.match(pattern, string)
    return bool(match)


def contain_num_and_str(string):
    pattern_str = "[a-zA-Z]"
    pattern_num = "[0-9]"
    return bool(re.search(pattern_str, string) and re.search(pattern_num, string))


class TheoremqaTask(Task):
    task_name = "reasoning"

    def __init__(self, id: str, prompt: str, reference: str, **kwargs):
        super().__init__(**kwargs)
        self._prompt = f"Answer the following question with a number, a list of numbers or True or False. {
            prompt.strip()
        }"
        self._reference = reference
        self._id = id
        self._answer_type = kwargs.get("answer_type")

    def _normalize_prediction_string(self, prediction: str) -> str:
        """Normalize prediction string by removing common formatting artifacts."""
        if "=" in prediction:
            prediction = prediction.split("=")[-1].strip()
        if "≈" in prediction:
            prediction = prediction.split("≈")[-1].strip()
        if "`" in prediction:
            prediction = prediction.replace("`", "")
        if "$" in prediction:
            prediction = prediction.replace("$", "")
        if "°" in prediction:
            prediction = prediction.replace("°", "")
        if "approximately" in prediction:
            prediction = prediction.replace("approximately", "").strip()
        if " or " in prediction:
            prediction = prediction.split(" or ")[0]
        return prediction

    def _handle_boolean_predictions(self, prediction: str) -> str:
        """Handle boolean predictions."""
        if prediction in {"true", "yes", "false", "no"}:
            prediction = "True" if prediction in {"true", "yes"} else "False"
        if "True" in prediction or "False" in prediction:
            prediction = "True" if "True" in prediction else "False"
        return prediction

    def _extract_numeric_values(self, prediction: str) -> str:
        """Extract numeric values from prediction using regex patterns."""
        patterns = [
            (r"[-+]?(?:[\d,]*\.*\d+) [^0-9 ]+$", r"([-+]?(?:[\d,]*\.*\d+)) [^0-9 ]+$"),
            (r"[^0-9 ]+ [-+]?(?:[\d,]*\.*\d+)$", r"[^0-9 ]+ ([-+]?(?:[\d,]*\.*\d+))$"),
            (
                r"[-+]?(?:[\d,]*\.*\d+)[^\d]{1,2}$",
                r"([-+]?(?:[\d,]*\.*\d+))[^\d]{1,2}$",
            ),
            (r"[^-+\d]{1,2}(?:[\d,]*\.*\d+)$", r"[^-+\d]{1,2}((?:[\d,]*\.*\d+))$"),
        ]

        for pattern, extract_pattern in patterns:
            if re.match(pattern, prediction):
                if match := re.search(extract_pattern, prediction):
                    prediction = match[1]
                    break
        return prediction

    def _handle_mathematical_expressions(self, prediction: str) -> str:
        """Handle mathematical expressions in prediction."""
        if "10^" in prediction:
            prediction = re.sub(r"10\^(-?\d+)", r"math.pow(10, \1)", prediction)
        if " x " in prediction:
            prediction = prediction.replace(" x ", "*")
        if " × " in prediction:
            prediction = prediction.replace(" × ", "*")
        if is_number(prediction):
            prediction = prediction.replace(",", "")
        return prediction

    def _handle_multiple_choice_options(self, prediction: str) -> str:
        """Handle multiple choice options (a, b, c, d)."""
        options = ["a", "b", "c", "d"]
        for option in options:
            if (
                f"{option})" in prediction
                or f"{option} )" in prediction
                or prediction.lower().strip() == option
            ):
                prediction = f"({option})"
                break

        if any(f"({option})" in prediction for option in options):
            if match := re.search(r"\([a-d]\)", prediction):
                prediction = f'"{match[0]}"'
        return prediction

    def _convert_prediction_to_result(self, prediction: str) -> Any:
        """Convert prediction string to final result."""
        if not prediction:
            prediction = "0"

        try:
            prediction = ast.literal_eval(prediction)  # nosec B307 - Safe: parsing controlled output
        except Exception:
            LOGGER.warning(
                f"[TASK] Failed to convert the answer: {prediction}\n{traceback.format_exc()}"
            )
            return None

        return self._normalize_result_types(prediction)

    def _normalize_result_types(self, prediction: Any) -> Any:
        """Normalize different result types to consistent format."""
        if isinstance(prediction, (set, tuple)):
            return self._normalize_sequence_types(prediction)
        elif isinstance(prediction, np.ndarray):
            return prediction.tolist()
        elif isinstance(prediction, complex):
            return prediction.real
        elif isinstance(prediction, Rational):
            return float(prediction)
        return prediction

    def _normalize_sequence_types(self, prediction: Any) -> list:
        """Normalize sequence types (set, tuple) to list with proper element conversion."""
        prediction = list(prediction)
        if not prediction:
            return prediction

        if isinstance(prediction[0], complex):
            return [tmp.real for tmp in prediction]
        elif isinstance(prediction[0], Rational):
            return [float(tmp) for tmp in prediction]
        return prediction

    def extract_answer(self, solution: str) -> Any:
        """Extract the answer from the given solution."""
        prediction = solution
        if not isinstance(prediction, str):
            prediction = prediction if prediction is not None else "0"

        prediction = self._normalize_prediction_string(prediction)
        prediction = self._handle_boolean_predictions(prediction)
        prediction = self._extract_numeric_values(prediction)
        prediction = self._handle_mathematical_expressions(prediction)
        prediction = self._handle_multiple_choice_options(prediction)

        return self._convert_prediction_to_result(prediction)

    def success(self, solution: str) -> bool:
        """This checks whether the given solution can complete the current task."""
        prediction = self.extract_answer(solution)
        LOGGER.info(f"TheoremQA Parsed Prediction: {prediction}")
        answer_type = self._answer_type
        gt = self.extract_answer(self.reference)
        if isinstance(prediction, (str, int, float, list)):
            if answer_type in ["bool", "option", "Option"]:
                cur_correct = int(prediction == f"({gt})") or int(prediction == gt)
            elif answer_type in ["integer", "float"]:
                cur_correct = int(compare_two_numbers(prediction, gt))
            elif answer_type in ["list of integer", "list of float"]:
                cur_correct = int(compare_two_list(prediction, gt))
        else:
            cur_correct = 0
        return bool(cur_correct)
