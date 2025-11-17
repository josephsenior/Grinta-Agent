import json
import logging
from openai import OpenAI
from .lm_utils import run_chatgpt_query_multi_turn
from .openai_helpers import get_response

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s -   %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _score_context_answer(answer: str) -> float:
    """Score context type answer."""
    answer = answer.replace("Answer:", "").strip()
    if answer.startswith("A)"):
        return 1.0
    elif answer.startswith("B)"):
        return 0.0
    return -1.0


def _score_rel_answer(answer: str) -> float:
    """Score relation type answer."""
    print(answer)
    rel_json = json.loads(answer)
    answer_str = rel_json["answer"].strip()

    if answer_str.startswith("A") or "very similar" in answer_str:
        return 1.0
    elif answer_str.startswith("B") or "similar but general than HypoA" in answer_str:
        return 0.5
    elif answer_str.startswith("C") or "different" in answer_str:
        return 0.0
    return -1.0


def _score_var_answer(answer: str) -> dict:
    """Score variable type answer."""
    try:
        var_json = json.loads(answer)
        f1 = 0.0
        p = var_json["intersection"] / var_json["sizeB"] if var_json["sizeB"] else 0.0

        r = var_json["intersection"] / var_json["sizeA"] if var_json["sizeA"] else 0.0
        f1 = 2 * p * r / (p + r) if p > 0.0 and r > 0.0 else 0.0

        eval_rec = {
            "p": p,
            "r": r,
            "f1": f1,
            "sizeA": var_json["sizeA"],
            "sizeB": var_json["sizeB"],
            "intersection": var_json["intersection"],
            "explanation": var_json["explanation"],
        }
        print(f"var_eval: {eval_rec}")
        return eval_rec
    except Exception:
        return {"p": -1.0, "r": -1.0, "f1": -1.0}


def get_score_from_answer(type, answer):
    """Get score from answer based on type."""
    if type == "context":
        return _score_context_answer(answer)
    elif type == "rel":
        return _score_rel_answer(answer)
    elif type == "var":
        return _score_var_answer(answer)
    return -1.0


def ask_dimension_question(
    query,
    gold_hypo,
    gold_workflow,
    gen_hypo,
    gen_workflow,
    dataset_meta,
    llm_used,
    dimension,
    dataset_type,
    use_column_metadata=True,
):
    dimension_question = ""
    answer = ""
    score = 0.0
    if dimension == "var":
        score = {"p": -1.0, "r": -1.0, "f1": -1.0}
    num_tokens = 256
    num_retries = 1
    json_response = False
    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant that helps evaluate a data-driven hypothesis. You are a helpful assistant who is not talkative. You only respond with the exact answer to a query without additional conversation.",
        }
    ]
    if dimension == "context":
        dimension_question = "        Question: Is HypoB defined in the same context as HypoA?\n        (Context refers to assumptions/stratification under which the hypotheses are defined.)\n        Options: A) same   B) different\n        What is your answer?"
    elif dimension == "rel":
        dimension_question = '        Question: Does HypoB exhibit the same relation as HypoA?\n        Compare using following example hierarchy of relationships (based on specificity):         "there exists a relationship" > "positive relationship" > "positive AND (linear OR quadratic)" > "positive AND linear".\n        Options: A) very similar B) similar but general than HypoA C) different\n        Return your answer as a JSON object in the following format:\n        ```json\n        {{\n        "answer": one of the options from A) very similar B) similar but general than HypoA C) different\n        "explanation": a short text explanation about the relationship comparison\n        }}```\n        Answer:'
        num_tokens = 512
        num_retries = 1
        json_response = True
    elif dimension == "var":
        dimension_question = '        Question: For both HypoA and HypoB, what are the different variables found in the hypotheses?         Return your answer as a JSON object in the following format:\n        ```json\n        {{\n        "sizeA": num of variables used in HypoA\n        "sizeB": num of variables used in HypoB\n        "intersection": num of variables common in HypoA and HypoB. Use *fuzzy matching* to determine intersection, accounting for paraphrases or slightly different surface forms\n        "explanation": a short text explanation about the variables\n        }}```\n        Answer:'
        num_tokens = 512
        num_retries = 1
        json_response = True
    datasets_json = prepare_dataset_metadata_json(
        dataset_meta, dataset_type=dataset_type, use_column_metadata=use_column_metadata
    )
    dimension_question_str = f'        You are going to compare two natural-language hypotheses HypoA and HypoB accompanied with optional workflows: WorkflowA for HypoA and WorkflowB for HypoB.         Both the hypotheses answer the natural language query "QUERY" over the dataset(s) described by dataset description(s) and column description(s) below.         Compare HypoA and HypoB in terms of three aspects: Contexts, Variables, and Relations.         E.g., for the hypothesis "From 1995 to 2009, the number of sandhill cranes around the tundra (Indigilka River) surged by an astounding ~10X":\n        * Contexts refer to stratification of the data under which the given hypothesis is True. E.g., "For all women", "From 1995 to 2009".\n        * Variables refer to the set of variables (either dependent or independent) that are mentioned in the hypothesis. E.g., number of sandhill cranes, location.\n        * Relations refer to the form of relation between the variables. E.g., "surged by ~10x".\n\n        Answer following questions for a given pair of hypotheses, HypoA and HypoB, along with an explanation grounded on the QUERY and the DATASET(S).\n\n        Here is the metadata for the task:\n        ```json\n        {{\n        "datasets": {datasets_json},\n        "query": {query},\n        "HypoA": {gold_hypo},\n        "WorkflowA": {gold_workflow},\n        "HypoB": {gen_hypo},\n        "WorkflowB": {gen_workflow}\n        }}\n        ```\n\n        {dimension_question}'
    messages.append({"role": "user", "content": dimension_question_str})
    for _ in range(num_retries):
        response = run_chatgpt_query_multi_turn(
            messages=messages,
            model_name=llm_used,
            max_tokens=num_tokens,
            temperature=0,
            json_response=json_response,
        )
        if response is not None:
            break
    if response is not None:
        answer = response.choices[0].message.content.strip()
        score = get_score_from_answer(type=dimension, answer=answer)
    return (dimension_question, answer, score)


def prepare_dataset_metadata_json(dataset_meta, dataset_type, use_column_metadata=True):
    if dataset_meta is None:
        return [{"dataset_description": "", "columns": []}]
    datasets_json = []
    for d in dataset_meta["datasets"]:
        if dataset_type == "real":
            datasets_json.append(
                {
                    "dataset_description": d["description"],
                    "columns": (
                        [
                            {"name": col["name"], "description": col["description"]}
                            for col in d["columns"]["raw"]
                        ]
                        if use_column_metadata
                        else []
                    ),
                }
            )
        else:
            datasets_json.append(
                {
                    "dataset_description": d["description"],
                    "columns": (
                        [
                            {"name": col["name"], "description": col["description"]}
                            for col in d["columns"]
                        ]
                        if use_column_metadata
                        else []
                    ),
                }
            )
    return datasets_json


def get_sub_hypotheses(
    query,
    hypo,
    workflow,
    dataset_meta,
    llm_used,
    dataset_type,
    use_column_metadata=True,
):
    client = OpenAI()
    extraction_prompt = '        Given a set of dataset columns, a ground-truth hypothesis, and the analysis workflow used, your task is to extract three dimensions that define the hypothesis: Context, Variables, and Relations.         Here are the definitions for these dimensions:\n        - Contexts: Boundary conditions that limit the scope of a hypothesis. E.g., “for men over         the age of 30”, “in Asia and Europe”. If the context applies to the full dataset, then extract the context from the dataset_descrption.\n        - Variables: Known concepts that interact in a meaningful way under a given context to         produce the hypothesis. E.g., gender, age, income, or "None" if there is no interacting variable.\n        - Relations: Interactions between a given set of variables under a given context to produce         the hypothesis. E.g., “quadratic relationship”, “inversely proportional”, piecewise conditionals,         or "None" if there is no interacting relationship.\n        Make sure to only use the information present in the hypothesis and the workflow. Do not add any new information.         For each dimension, be specific, and do not omit any important details.\n\n        Here is the metadata for the task:\n        ```json\n        {\n        "datasets": %s,\n        "hypothesis": "%s",\n        "workflow": "%s"\n        }\n        ```\n\n        Return your answer as a JSON object in the following format:\n        ```json\n        {\n        "sub_hypo": [\n            {\n                "text": the hypothesis in natural language,\n                "context": a short text description of the context of the hypothesis,\n                "variables": a list of columns involved in the hypothesis,\n                "relations": a short text description of the relationship between the variables of the hypothesis\n            },\n            ...\n        ]\n        }```\n        '
    datasets_json = prepare_dataset_metadata_json(
        dataset_meta, dataset_type, use_column_metadata=use_column_metadata
    )
    _prompt = extraction_prompt % (datasets_json, hypo, workflow)
    sub_hypo_json = get_response(client, _prompt, model=llm_used, max_retry=1)
    if sub_hypo_json is not None:
        print(f"sub_hypo_json: {sub_hypo_json}")
    else:
        sub_hypo_json = {"sub_hypo": []}
    sub_hypo_json["full_hypo"] = hypo
    return sub_hypo_json


def match_context_with_gpt(
    gold_hyp, gold_context, pred_hyp, pred_context, model="gpt-3.5-turbo"
):
    prompt = f'        Given a gold hypothesis, a gold context, a predicted hypothesis, and a predicted context, your task is         to determine if the predicted context semantically matches the ground-truth context.         Here is the definition for Context: Boundary conditions that limit the scope of a sub-hypothesis. E.g., “for men over the age of 30”, “in Asia and Europe”. If the context applies to the full dataset, then the context is derived from the dataset_descrption.         Here is the definition for Context: Boundary conditions that limit the scope of a sub-hypothesis. E.g., “for men over the age of 30”, “in Asia and Europe”. If the context applies to the full dataset, then the context is derived from the dataset_descrption.         If the predicted context matches the gold context, return true, otherwise return false.\n        If both gold and predicted hypotheses are defined over the context of the full dataset, then also return true.\n        If both gold and predicted hypotheses are defined over the context of the full dataset, then also return true.\n\n        Here is the metadata for the task:\n        ```json\n        {{\n            "gold_hypothesis": "{gold_hyp}",\n            "gold_context": "{gold_context}",\n            "predicted_hypothesis": "{pred_hyp}",\n            "predicted_context": "{pred_context}"\n        }}\n        ```\n\n        Return your answer as a JSON object in the following format:\n        ```json\n        {{\n            "match": true or false\n        }}\n        ```'
    client = OpenAI()
    output = get_response(client, prompt, model=model)
    return output.get("match", False)


def is_matching_context(gold_hyp, gold_context, pred_hyp, pred_context, llm_used):
    if gold_context == pred_context:
        return True
    if "None" in [gold_context, pred_context]:
        return False
    return match_context_with_gpt(
        gold_hyp, gold_context, pred_hyp, pred_context, model=llm_used
    )


def run_eval_gold_vs_gen_NL_subhypo(
    query,
    gold_hypo,
    gold_workflow,
    gen_hypo,
    gen_workflow,
    dataset_meta,
    llm_used,
    context_score,
    dataset_type,
    use_column_metadata=True,
):
    eval_rec = {
        "query": query,
        "HypoA": gold_hypo,
        "WorkflowA": gold_workflow,
        "HypoB": gen_hypo,
        "WorkflowB": gen_workflow,
    }
    for dimension in ["var", "rel"]:
        question, answer, score = ask_dimension_question(
            query,
            gold_hypo,
            gold_workflow,
            gen_hypo,
            gen_workflow,
            dataset_meta,
            llm_used,
            dimension=dimension,
            dataset_type=dataset_type,
            use_column_metadata=use_column_metadata,
        )
        eval_rec[dimension] = {"question": question, "answer": answer, "score": score}
    eval_rec["context"] = context_score
    eval_rec["accuracy_score"] = (
        1.0
        * eval_rec["context"]["score"]
        * eval_rec["var"]["score"]["f1"]
        * eval_rec["rel"]["score"]
    )
    return eval_rec


def _get_sub_hypotheses_with_fallback(
    query, hypo, workflow, dataset_meta, llm_used, dataset_type, use_column_metadata
):
    """Get sub-hypotheses with fallback if empty."""
    sub_hypo_json = get_sub_hypotheses(
        query=query,
        hypo=hypo,
        workflow=workflow,
        dataset_meta=dataset_meta,
        llm_used=llm_used,
        dataset_type=dataset_type,
        use_column_metadata=use_column_metadata,
    )

    if len(sub_hypo_json["sub_hypo"]) == 0:
        sub_hypo_json["sub_hypo"] = [
            {
                "text": hypo,
                "context": "None",
                "variables": [],
                "relations": "",
                "explanation": "unable to segment",
            }
        ]

    return sub_hypo_json


def _match_generated_to_gold_subhypotheses(
    gen_sub_hypo_json, gold_sub_hypo_json, llm_used
):
    """Match generated sub-hypotheses to gold sub-hypotheses."""
    gold_subh_covered = []
    gen_subh_to_gold_subh = {}
    gen_gold_subh_to_context = {}

    for p_id, gen_subh in enumerate(gen_sub_hypo_json["sub_hypo"]):
        gen_subh_to_gold_subh[p_id] = -1
        for g_id, gold_subh in enumerate(gold_sub_hypo_json["sub_hypo"]):
            if g_id in gold_subh_covered:
                continue

            context_bool = is_matching_context(
                gold_subh["text"],
                gold_subh.get("context", ""),
                gen_subh["text"],
                gen_subh.get("context", ""),
                llm_used,
            )
            context_score = 1.0 if context_bool else 0.0

            if context_score == 1.0:
                gen_subh_to_gold_subh[p_id] = g_id
                gold_subh_covered.append(g_id)
                gen_gold_subh_to_context[f"P{p_id}||G{g_id}"] = {
                    "question": f"Comapring: GoldH: {gold_subh['text']}, GoldC: {gold_subh['context']}\nGenH: {gen_subh['text']}, GenC: {gen_subh['context']}",
                    "answer": context_bool,
                    "score": context_score,
                }
                break

    return gen_subh_to_gold_subh, gold_subh_covered, gen_gold_subh_to_context


def _evaluate_matched_subhypotheses(
    gen_subh_to_gold_subh,
    gen_gold_subh_to_context,
    query,
    gold_hypo,
    gold_workflow,
    gen_hypo,
    gen_workflow,
    dataset_meta,
    llm_used,
    dataset_type,
    use_column_metadata,
):
    """Evaluate matched sub-hypotheses."""
    matched_gold_gen_subh_evals = {}
    sum_accuracy_score = 0.0

    for p_id, g_id in gen_subh_to_gold_subh.items():
        if g_id >= 0:
            key = f"P{p_id}||G{g_id}"
            context_score = gen_gold_subh_to_context[key]
            subh_eval_rec = run_eval_gold_vs_gen_NL_subhypo(
                query,
                gold_hypo,
                gold_workflow,
                gen_hypo,
                gen_workflow,
                dataset_meta,
                llm_used,
                context_score,
                dataset_type=dataset_type,
                use_column_metadata=use_column_metadata,
            )
            sum_accuracy_score += subh_eval_rec["accuracy_score"]
            matched_gold_gen_subh_evals[key] = subh_eval_rec

    return matched_gold_gen_subh_evals, sum_accuracy_score


def run_eval_gold_vs_gen_NL_hypo_workflow(
    query,
    gold_hypo,
    gold_workflow,
    gen_hypo,
    gen_workflow,
    dataset_meta,
    llm_used,
    dataset_type,
    use_column_metadata=True,
):
    """Run evaluation of gold vs generated NL hypothesis workflow."""
    eval_rec = {
        "query": query,
        "HypoA": gold_hypo,
        "WorkflowA": gold_workflow,
        "HypoB": gen_hypo,
        "WorkflowB": gen_workflow,
    }

    # Get sub-hypotheses for both gold and generated
    gold_sub_hypo_json = _get_sub_hypotheses_with_fallback(
        query,
        gold_hypo,
        gold_workflow,
        dataset_meta,
        llm_used,
        dataset_type,
        use_column_metadata,
    )
    print(f"gold_sub_hypo_json: {gold_sub_hypo_json}")

    gen_sub_hypo_json = _get_sub_hypotheses_with_fallback(
        query,
        gen_hypo,
        gen_workflow,
        dataset_meta,
        llm_used,
        dataset_type,
        use_column_metadata,
    )
    print(f"gen_sub_hypo_json: {gen_sub_hypo_json}")

    eval_rec["gold_sub_hypo"] = gold_sub_hypo_json
    eval_rec["gen_sub_hypo"] = gen_sub_hypo_json

    # Match generated to gold sub-hypotheses
    gen_subh_to_gold_subh, gold_subh_covered, gen_gold_subh_to_context = (
        _match_generated_to_gold_subhypotheses(
            gen_sub_hypo_json, gold_sub_hypo_json, llm_used
        )
    )

    print(f"gen_subh_to_gold_subh: {gen_subh_to_gold_subh}")
    eval_rec["gen_subh_to_gold_subh"] = gen_subh_to_gold_subh
    eval_rec["gold_subh_covered"] = gold_subh_covered

    # Evaluate matched sub-hypotheses
    matched_gold_gen_subh_evals, sum_accuracy_score = _evaluate_matched_subhypotheses(
        gen_subh_to_gold_subh,
        gen_gold_subh_to_context,
        query,
        gold_hypo,
        gold_workflow,
        gen_hypo,
        gen_workflow,
        dataset_meta,
        llm_used,
        dataset_type,
        use_column_metadata,
    )

    eval_rec["matched_gold_gen_subh_evals"] = matched_gold_gen_subh_evals
    eval_rec["recall_context"] = (
        len(gold_subh_covered) / len(gold_sub_hypo_json["sub_hypo"])
        if len(gold_sub_hypo_json["sub_hypo"])
        else 0.0
    )
    eval_rec["mean_accuracy_score"] = (
        sum_accuracy_score / len(gen_subh_to_gold_subh)
        if len(gen_subh_to_gold_subh)
        else 0.0
    )
    eval_rec["final_score"] = (
        eval_rec["recall_context"] * eval_rec["mean_accuracy_score"]
    )

    print(f"eval_rec: {json.dumps(eval_rec, indent=2)}")
    return eval_rec
