"""block completion."""

import copy
import gc
import json
import os
import time
from multiprocessing import Process
import tiktoken
import torch
from vllm import LLM, SamplingParams


def truncate_text(text, max_tokens):
    encoding = tiktoken.get_encoding("cl100k_base")
    disallowed_special = ()
    tokens = encoding.encode(text, disallowed_special=disallowed_special)
    print(len(tokens))
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return encoding.decode(tokens)


model_list = ["/data2/base models/starcoder2-15b", "/data2/base models/CodeGemma-7B"]


def run_inference(model_name, origin_data_list):
    temp_data_list = copy.deepcopy(origin_data_list)
    test_list = []
    for data in temp_data_list:
        version = data["dependency"] + data["version"]
        description = data["description"]
        instruction = bulid_prompt(version, description)
        test_list.append(instruction)
    sampling_params = SamplingParams(n=6, temperature=0.8, top_p=0.95, max_tokens=64)
    llm = LLM(model=model_name, tensor_parallel_size=4, gpu_memory_utilization=0.9, swap_space=20)
    outputs = llm.generate(test_list, sampling_params)
    for output in outputs:
        requests_id = int(output.request_id)
        temp_ans_list = []
        output_list = output.outputs
        temp_ans_list.extend((o.text for o in output_list))
        temp_data_list[requests_id]["model_output"] = str(temp_ans_list)
    save_folder_path = os.path.join("../data/result_data/block_completion", model_name.split("/")[-1])
    if not os.path.exists(save_folder_path):
        os.makedirs(save_folder_path)
    save_json_path = os.path.join(save_folder_path, json_path.split("/")[-1])
    with open(save_json_path, "w", encoding="utf-8") as fw:
        json.dump(temp_data_list, fw, indent=4, ensure_ascii=False)
    gc.collect()
    torch.cuda.empty_cache()


def bulid_prompt(version, description) -> str:
    """Build prompt.

    :param version:
    :param description:
    :param masked_code:
    :param options:
    :return:
    """
    return f'\n            You are a professional Python engineer, and I will provide functional descriptions and versions of specified dependency packages.\n            You need to write code in Python to implement this feature based on the functional description and using the dependency package and version I specified.\n            Please note that you only need to return the code that implements the function, and do not return any other content.\n            Please use <start> and <end> to enclose the generated code. Here is an example:\n            ###Function Description：\n            The function of this code is to print the results predicted by calling the model using vllm.\n            ###dependeny and version：\n            vllm==0.3.3\n            ###response:\n            <start>\n            for output in outputs:\n                prompt = output.prompt\n                generated_text = output.outputs[0].text\n                print("Prompt,Generated text")\n            <end>\n\n            ###Function Description：\n            {description}\n            ###dependeny and version：\n            {version}\n            ###response:\n\n\n        '


json_path = "../data/test_data/VersiCode_block_completion.json"
with open(json_path, "r", encoding="utf-8") as fr:
    lodict = json.load(fr)
origin_data_list = lodict
for model_name in model_list:
    process = Process(target=run_inference, args=(model_name, origin_data_list))
    process.start()
    process.join()
    time.sleep(120)
