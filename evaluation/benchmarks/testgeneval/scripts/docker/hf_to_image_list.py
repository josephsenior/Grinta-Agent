from datasets import load_dataset


def dataset_to_txt(dataset, txt_file, split="test"):
    with open(txt_file, "w", encoding="utf-8") as f:
        for datum in dataset[split]:
            instance_id = datum["instance_id"].replace("__", "_s_")
            f.write(f"sweb.eval.x86_64.{instance_id}:latest\n")


if __name__ == "__main__":
    dataset = load_dataset("kjain14/testgeneval")  # nosec B615 - Safe: evaluation benchmark dataset
    dataset_lite = load_dataset("kjain14/testgenevallite")  # nosec B615 - Safe: evaluation benchmark dataset
    dataset_to_txt(dataset_lite, "all-swebench-lite-instance-images.txt", lite=True)
    dataset_to_txt(dataset, "all-swebench-full-instance-images.txt")
