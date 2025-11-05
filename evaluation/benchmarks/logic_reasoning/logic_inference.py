import os
import random
import re
import shutil
from pyke import knowledge_engine


class PykeProgram:

    def __init__(self, logic_program: str, dataset_name="ProntoQA", workspace_mount_path="./") -> None:
        self.logic_program = logic_program
        self.flag = self.parse_logic_program()
        self.dataset_name = dataset_name
        self.cache_dir = os.path.join(workspace_mount_path, ".cache_program")
        try:
            self.create_fact_file(self.Facts)
            self.create_rule_file(self.Rules)
            self.flag = True
        except Exception:
            self.flag = False
        self.answer_map = {"ProntoQA": self.answer_map_prontoqa, "ProofWriter": self.answer_map_proofwriter}

    def parse_logic_program(self):
        keywords = ["Query:", "Rules:", "Facts:", "Predicates:"]
        program_str = self.logic_program
        for keyword in keywords:
            try:
                program_str, segment_list = self._parse_segment(program_str, keyword)
                setattr(self, keyword[:-1], segment_list)
            except Exception:
                setattr(self, keyword[:-1], None)
        return self.validate_program()

    def _parse_segment(self, program_str, key_phrase):
        remain_program_str, segment = program_str.split(key_phrase)
        segment_list = segment.strip().split("\n")
        for i in range(len(segment_list)):
            segment_list[i] = segment_list[i].split(":::")[0].strip()
        return (remain_program_str, segment_list)

    def validate_program(self):
        if self.Rules is not None and self.Facts is not None and (self.Rules[0] != "" and self.Facts[0] != ""):
            return True
        tmp_rules = []
        tmp_facts = []
        statements = self.Facts if self.Facts is not None else self.Rules
        if statements is None:
            return False
        for fact in statements:
            if fact.find(">>>") >= 0:
                tmp_rules.append(fact)
            else:
                tmp_facts.append(fact)
        self.Rules = tmp_rules
        self.Facts = tmp_facts
        return False

    def create_fact_file(self, facts):
        with open(os.path.join(self.cache_dir, "facts.kfb"), "w") as f:
            for fact in facts:
                if fact.find("$x") < 0:
                    f.write(fact + "\n")

    def create_rule_file(self, rules):
        pyke_rules = [self.parse_forward_rule(idx + 1, rule) for idx, rule in enumerate(rules)]
        with open(os.path.join(self.cache_dir, "rules.krb"), "w") as f:
            f.write("\n\n".join(pyke_rules))

    def parse_forward_rule(self, f_index, rule):
        premise, conclusion = rule.split(">>>")
        premise = premise.strip()
        premise = premise.split("&&")
        premise_list = [p.strip() for p in premise]
        conclusion = conclusion.strip()
        conclusion = conclusion.split("&&")
        conclusion_list = [c.strip() for c in conclusion]
        pyke_rule = f"fact{f_index}\n\tforeach"
        for p in premise_list:
            pyke_rule += f"\n\t\tfacts.{p}"
        pyke_rule += "\n\tassert"
        for c in conclusion_list:
            pyke_rule += f"\n\t\tfacts.{c}"
        return pyke_rule

    "\n    for example: Is Marvin from Mars?\n    Query: FromMars(Marvin, $label)\n    "

    def check_specific_predicate(self, subject_name, predicate_name, engine):
        results = []
        with engine.prove_goal(f"facts.{predicate_name}({subject_name}, $label)") as gen:
            results.extend((vars["label"] for vars, plan in gen))
        with engine.prove_goal(f"rules.{predicate_name}({subject_name}, $label)") as gen:
            results.extend((vars["label"] for vars, plan in gen))
        if len(results) == 1:
            return results[0]
        elif len(results) == 2:
            return results[0] and results[1]
        elif not results:
            return None

    "\n    Input Example: Metallic(Wren, False)\n    "

    def parse_query(self, query):
        pattern = "(\\w+)\\(([^,]+),\\s*([^)]+)\\)"
        if not (match := re.match(pattern, query)):
            raise ValueError(f"Invalid query: {query}")
        function_name = match[1]
        arg1 = match[2]
        arg2 = match[3]
        arg2 = arg2 == "True"
        return (function_name, arg1, arg2)

    def execute_program(self):
        complied_krb_dir = "./models/compiled_krb"
        if os.path.exists(complied_krb_dir):
            print("removing compiled_krb")
            shutil.rmtree(complied_krb_dir)
        try:
            engine = knowledge_engine.engine(self.cache_dir)
            engine.reset()
            engine.activate("rules")
            engine.get_kb("facts")
            predicate, subject, value_to_check = self.parse_query(self.Query[0])
            result = self.check_specific_predicate(subject, predicate, engine)
            answer = self.answer_map[self.dataset_name](result, value_to_check)
        except Exception as err:
            return (None, err)
        return (answer, "")

    def answer_mapping(self, answer):
        return answer

    def answer_map_prontoqa(self, result, value_to_check):
        return "A" if result == value_to_check else "B"

    def answer_map_proofwriter(self, result, value_to_check):
        if result is None:
            return "C"
        elif result == value_to_check:
            return "A"
        else:
            return "B"


class LogicInferenceEngine:

    def __init__(self):
        self.dataset_name = os.environ.get("DATASET_NAME", "ProofWriter")
        self.workspace_mount_path = "/workspace"

    def random_backup(self):
        if self.dataset_name == "ProntoQA":
            return random.choice(["A", "B"])
        elif self.dataset_name == "ProofWriter":
            return random.choice(["A", "B", "C"])

    def safe_execute_program(self, logic_program):
        program = PykeProgram(logic_program, self.dataset_name, self.workspace_mount_path)
        if not program.flag:
            answer = self.random_backup()
            return (answer, "parsing error", "")
        answer, error_message = program.execute_program()
        if answer is None:
            answer = self.random_backup()
            return (answer, "execution error", error_message)
        answer = program.answer_mapping(answer)
        return (answer, "success", "")
