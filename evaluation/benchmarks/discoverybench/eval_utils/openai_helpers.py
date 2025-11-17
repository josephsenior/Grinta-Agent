import json


def OPENAI_TOPIC_GEN_MESSAGES(n=10):
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant who is not talkative. You only respond with the exact answer to a query without additional conversation.",
        },
        {
            "role": "user",
            "content": f'Given `n`, come up with a list of `n` distinct topics and their descriptions. The topics can be absolutely anything. Be as creative as possible. Return your answer as a JSON object. \n\nFor example, for `n`=3, a valid answer might be:\n```json\n{
                "topics": [\n  {
                    "id": 1, "topic": "cooking", "description": "Related to recipes, ingredients, chefs, etc."} ,\n  {
                    "id": 2, "topic": "sports", "description": "Related to players, stadiums, trophies, etc."} ,\n  {
                    "id": 3, "topic": "antiquing", "description": "Related to unique items, history, etc."} \n]} ```\n\nNow, give me a list for `n`={
                n
            }. Remember, pick diverse topics from everything possible. No consecutive topics should be broadly similar. Directly respond with the answer JSON object.',
        },
    ]


OPENAI_GEN_HYP = {
    "temperature": 1.0,
    "max_tokens": 4096,
    "top_p": 1.0,
    "frequency_penalty": 0,
    "presence_penalty": 0,
}


def OPENAI_SEMANTICS_GEN_MESSAGES(dependent, relationship, domain, domain_desc):
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant who is not talkative. You only respond with the exact answer to a query without additional conversation.",
        },
        {
            "role": "user",
            "content": f"""Given the true relationship in a dataset and a given domain, your task is to come up with an interpretation of some real-world concepts that the relationship could be modeling from the provided domain. It's okay to be wrong, but suggest something reasonable. Try as much as possible to make sure that the TARGET is actually derivable from the other variables. Give your answer as a JSON object. Here's an example:

Relationship for x2 = "(96.4 * x1 ** 3) + (88.72 * x5 ** 2) + (81.96 * x6 ** -2) + (28.13 * x3)  + (97.0) + (0 * x4)"
Domain="Sales"
Domain description="Related to product distribution, revenues, marketing, etc."

Based on this, the following real-world concepts might be applicable:
```json
{{
  "dependent": "x2",
  "relationship": "(96.4 * x1 ** 3) + (88.72 * x5 ** 2) + (81.96 * x6 ** -2) + (28.13 * x3)  + (97.0) + (0 * x4)",
  "domain": "Sales",
  "trends": {{
    "x1": "Positive, cubic factor",
    "x2": "TARGET",
    "x3": "Positive, linear factor",
    "x4": "No relation",
    "x5": "Positive quadratic factor",
    "x6": "Positive, inverse quadratic factor"
  }},
  "interpretation": {{
    "x2": {{"description": "Volume of product sales by area", "name": "sales_area", "is_target": true}},
    "x1": {{"description": "Population by area", "name": "pop_area"}},
    "x3": {{"description": "Advertising spending", "name": "ad_spend"}},
    "x4": {{"description": "Gender ratio of marketing team", "name": "gdr_ratio_mkt_team"}},
    "x5": {{"description": "Intensity of marketing campaign", "name": "mkt_intensity"}}
  }},
    "x6": {{"description": "Distance to distribution center", "name": "dist_to_distr_ctr"}}
}}```

Here's a new test question:
Relationship for {dependent} = "{relationship}"
Domain = "{domain}"
Domain description="{domain_desc}"

Respond only with the answer JSON. Make sure that you do not forget to include the TARGET variable in the interpretation object.""",
        },
    ]


def OPENAI_SEMANTICS_GEN_W_MAP_MESSAGES(
    dependent, relationship, domain, domain_desc, mapping
):
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant who is not talkative. You only respond with the exact answer to a query without additional conversation.",
        },
        {
            "role": "user",
            "content": f"""Given a partial mapping from variables to real-world concepts and a true relationship in a dataset, your task is to come up with an interpretation of real-world concepts for the variables without any assigned mapping (those starting with x). Suggest something reasonable. The dependent variable must be derivable only from the other variables in the dependent relationship. Give your answer as a JSON object. Here's an example:

Example partial mapping and relationship:
```json
{{
  "domain": "Sales",
  "domain_description": "Related to product distribution, revenues, marketing, etc.",
  "variable_mapping": {{
    "x1": {{"description": "Population by area", "name": "pop_area"}},
    "x2": {{"description": "Volume of product sales by area", "name": "sales_area"}},
    "x4": {{"description": "Gender ratio of marketing team", "name": "gdr_ratio_mkt_team"}},
    "x6": {{"description": "Distance to distribution center", "name": "dist_to_distr_ctr"}}
  }},
  "dependent_variable": "sales_area",
  "dependent_relationship": "(96.4 * pop_area ** 3) + (88.72 * x5 ** 2) + (81.96 * dist_to_distr_ctr ** -2) + (28.13 * x3)  + (97.0)"
}}```
Based on this, an example answer would be:
```json
{{
  "dependent_variable": "sales_area",
  "missing_mapping": ["x3", "x5"],
  "trends": {{
    "x3": "Positive, linear factor",
    "x5": "Positive quadratic factor"
  }},
  "interpretation": {{
    "x3": {{"description": "Advertising spending", "name": "ad_spend"}},
    "x5": {{"description": "Intensity of marketing campaign", "name": "mkt_intensity"}}
  }}
}}```

Here's a new test question:
```json
{{
  "domain": "{domain}",
  "domain_description": "{domain_desc}",
  "variable_mapping": {json.dumps(mapping, indent=2)},
  "dependent_variable": "{dependent}",
  "dependent_relationship": "{relationship}"
}}```
Respond only with the answer JSON.""",
        },
    ]


def OPENAI_SEMANTICS_GEN_SUMMARY_MESSAGES(dataset):
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant who is not talkative. You only respond with the exact answer to a query without additional conversation.",
        },
        {
            "role": "user",
            "content": f"""Given the following descriptions of the columns of a dataset, your task is to come up with a natural language overview of the dataset, which should include (1) what the dataset is about, (2) how the data was collected, (3) when the data was collected, and (3) for what purpose the data was collected. Be specific and creative.

Example dataset:
```json
{{
  "dataset": {{
    "x6": {{"description": "Ancient artifact significance score", "name": "artifact_significance_score", "is_target": true}},
    "x1": {{"description": "Distance to ancient city center", "name": "dist_to_ancient_city_ctr"}},
    "x2": {{"description": "Quantity of discovered relics", "name": "relic_discovery_qty"}},
    "x3": {{"description": "Years since last archaeological expedition", "name": "years_since_exp"}},
    "x4": {{"description": "Number of artifacts in excavation site", "name": "artifact_qty"}},
    "x5": {{"description": "Soil fertility coefficient", "name": "soil_fertility_coef"}},
    "x7": {{"description": "Distance to ancient burial grounds", "name": "dist_to_burial_grounds"}},
    "x8": {{"description": "Population estimate of ancient civilization", "name": "ancient_civilization_pop_estimate"}},
    "x9": {{"description": "Temperature variation in excavation region", "name": "temp_variation"}}
  }}
}}```
Example description:
This dataset is about archaeological explorations and findings linked to ancient civilizations. The data was collected in the form of field metrics during various archaeological expeditions during the late mid-20th century. The purpose of the data collection is to evaluate the significance of ancient artifacts discovered during excavations.

Here is a new test dataset.
{json.dumps(dataset, indent=2)}
Provide only the description.""",
        },
    ]


def OPENAI_GEN_HYPO_MESSAGES(dataset):
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant who is not talkative. You only respond with the exact answer to a query without additional conversation.",
        },
        {
            "role": "user",
            "content": f"""Given a dataset with its descriptions and the true functional relationship between its variables, your task is to generate 3 levels of hypotheses for the stated relationship in plain English. The three levels are "broad", "medium" and "narrow". Make sure that the hypotheses sound natural. *Only include concepts for variables that are present in the provided functional relationship.* Give your answer as a JSON.

For example, an example dataset might be the following:
```json
{{
  "domain": "cybersecurity",
  "summary": "This dataset is about measuring cybersecurity threats in a system. The data was collected by monitoring various cybersecurity metrics in a network environment. The purpose of the data collection is to assess and predict potential cybersecurity risks and vulnerabilities.",
  "variables": [
    {{
      "description": "Level of cybersecurity threat",
      "name": "cybersecurity_threat",
      "is_target": true
    }},
    {{
      "description": "Number of failed login attempts",
      "name": "failed_login_attempts"
    }},
    {{
      "description": "Amount of encrypted data",
      "name": "encrypted_data"
    }},
    {{
      "description": "Frequency of software updates",
      "name": "software_updates"
    }},
    {{
      "description": "Number of antivirus software installed",
      "name": "antivirus_software"
    }},
    {{
      "description": "Quality of firewall protection",
      "name": "firewall_quality"
    }}
  ],
  "relationship": {{
    "dependent": "cybersecurity_threat",
    "relation": "-53.5*encrypted_data**2 - 53.85*failed_login_attempts**2 + 67.75*firewall_quality - 92.16 - 36.68/software_updates**3"
  }}
}}```
Given this dataset, the following is a valid answer:
```json
{{
  "broad": {{
    "instruction": "Be vague. Only indicate which concepts might be related but not how they are related",
    "hypothesis": "Threat to cybersecurity is influenced by several factors including the amount of encrypted data, the number of failed login attempts, the quality of the firewall, as well as how often the software is updated."
  }},
  "medium": {{
    "instruction": "Be slightly more specific. For each factor, indicate carefully whether it positively or negatively affects the relationship, but do not indicate what the exponent is.",
    "hypothesis": "Cybersecurity threat tends to decrease with the amount of data encryption, the number of failed login attempts, as well as the frequency of software updates to some extent, while improvement in the firewall quality has a positive effect."
  }},
  "narrow": {{
    "instruction": "Be specific. Communicate the concepts, whether there is a positive or negative effect (be careful), and the meaning of the exponent",
    "hypothesis": "The threat to cybersecurity interacts in a complex manner with various factors. As the amount of encrypted data increases, there is a quadratic decrease in threat. Similarly for the number of failed login attempts, there is a negative quadratic relationship. The quality of the firewall protection on the other hand demonstrates a positive and linear relationship. Finally, the frequency of software updates has an inverse cubic relationship to the threat."
  }},
}}
```

Based on this, provide an answer for the following test dataset:
```json
{dataset}```
Respond only with a JSON.""",
        },
    ]


def create_prompt(usr_msg):
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant who is not talkative. You only respond with the exact answer to a query without additional conversation.",
        },
        {"role": "user", "content": usr_msg},
    ]


def get_response(client, prompt, max_retry=5, model="gpt-3.5-turbo", verbose=False):
    n_try = 0
    while n_try < max_retry:
        response = client.chat.completions.create(
            model=model, messages=create_prompt(prompt), **OPENAI_GEN_HYP
        )
        content = response.choices[0].message.content
        cleaned_content = content.split("```json")[1].split("```")[0].strip()
        output = cleaned_content
        try:
            return json.loads(output)
        except ValueError:
            if verbose:
                print(f"Bad JSON output:\n\n{output}")
            n_try += 1
            if verbose:
                if n_try < max_retry:
                    print("Retrying...")
                else:
                    print("Retry limit reached")
    return None


def get_code_fix(
    client, code, error, max_retry=5, model="gpt-3.5-turbo", verbose=False
):
    prompt = f"""Given the following code snippet and error message, provide a single-line fix for the error. Note that the code is going to be executed using python `eval`. The code should be executable and should not produce the error message. Be as specific as possible.

Here's the code and the error:
{{
    "code": "{code}",
    "error": "{error}"
}}

Return only a JSON object with the fixed code in the following format:
```json
{{
    "fixed_code": "..."
}}"""
    return get_response(
        client, prompt, max_retry=max_retry, model=model, verbose=verbose
    )


def get_new_hypothesis(
    client, target, old, expr, cols, model="gpt-3.5-turbo", verbose=False
):
    prompt = f"""Given a target column from a dataset, a pandas expression to derive the column from existing columns, a list of existing columns, and a previously written hypothesis text, carefully check if the hypothesis text is consistent with the pandas expression or not. If it is consistent, simply return the hypothesis as it is. If it is not consistent, provide a new natural language hypothesis that is consistent with the pandas expression using only the provided information. Be specific.

Here's the information:
```json
{{
    "target_column": "{target}",
    "pandas_expression": "{expr}",
    "existing_columns": {json.dumps(cols, indent=4)},
    "old_hypothesis": "{old}",
}}```

Give your answer as a new JSON with the following format:
```json
{{
    "hypothesis": "..."
}}"""
    return get_response(client, prompt, model=model, verbose=verbose)


def replace_variable(client, expr, old, new, model="gpt-3.5-turbo", verbose=False):
    prompt = f"""Given a pandas "expression", replace mentions of the "old" column with its "new" value such that the resultant expression is equivalent to the original expression.

Here's the information:
```json
{{
    "expression": "{expr}",
    "old": "{old}",
    "new": "{new}"
}}```

Give your answer as a new JSON with the following format:
```json
{{
    "new_expression": "..."
}}"""
    return get_response(client, prompt, model=model, verbose=verbose)
