import argparse
import os
import subprocess
from datasets import load_dataset


def run_command(command):
    try:
        cmd_args = command.split() if isinstance(command, str) else command
        subprocess.run(cmd_args, check=True, shell=False)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")


def docker_login():
    print("Logging into Docker Hub...")
    run_command("docker login")


def generate_dockerfile_content(base_image, dependencies, datum, patch_path, test_patch_path):
    dockerfile_content = f'\nFROM {base_image}\nSHELL ["/bin/bash", "-c"]\nRUN source /opt/miniconda3/bin/activate && conda activate testbed && pip install {
        ' '.join(dependencies)}\nCOPY {patch_path} /app/patch.diff\nRUN git apply /app/patch.diff\nRUN rm /app/patch.diff\nCOPY {test_patch_path} /app/patch.diff\nRUN git apply /app/patch.diff\nRUN git config --global user.email ""\nRUN git config --global user.name "TestGenEval"\nRUN rm /app/patch.diff\nRUN rm {
        datum['test_file']}\n'
    dockerfile_content += 'RUN git add .\nRUN git commit -m "Testing fixes"'
    return dockerfile_content


def build_and_push_image(dockerfile_content, image_name):
    with open("Dockerfile.temp", "w", encoding='utf-8') as dockerfile:
        dockerfile.write(dockerfile_content)
    run_command(f"docker build -f Dockerfile.temp -t {image_name} .")
    run_command(f"docker push {image_name}")
    run_command(f"docker rmi {image_name}")
    os.remove("Dockerfile.temp")


def process_images(dataset, original_namespace, new_namespace, start_instance_id):
    dependencies = ["coverage", "cosmic-ray"]
    found_start = len(start_instance_id) == 0
    for datum in dataset:
        if not found_start and datum["instance_id"] == start_instance_id:
            found_start = True
        elif found_start:
            full_image_name = f"{original_namespace}/sweb.eval.x86_64.{
                datum['instance_id'].replace(
                    '__', '_s_')}:latest"
            print(f"Processing image: {full_image_name}")
            run_command(f"docker pull {full_image_name}")
            patch_file_path = "patch.diff"
            test_patch_file_path = "test_patch.diff"
            with open(patch_file_path, "w", encoding='utf-8') as patch_file, open(test_patch_file_path, "w", encoding='utf-8') as test_patch_file:
                patch_file.write(datum["patch"])
                test_patch_file.write(datum["test_patch"])
            new_image_name = f"{new_namespace}/sweb.eval.x86_64.{datum['instance_id'].replace('__', '_s_')}:latest"
            dockerfile_content = generate_dockerfile_content(
                full_image_name, dependencies, datum, patch_file_path, test_patch_file_path
            )
            build_and_push_image(dockerfile_content, new_image_name)
            os.remove(patch_file_path)
            os.remove(test_patch_file_path)
            run_command(f"docker rmi {full_image_name}")
            run_command("docker system prune -f")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Docker images with .eval in the name.")
    parser.add_argument("--dataset", type=str, default="kjain14/testgeneval")
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument(
        "--new_namespace", type=str, default="kdjain", help="The new Docker Hub namespace to push the images"
    )
    parser.add_argument("--original_namespace", type=str, default="xingyaoww", help="The original Docker Hub namespace")
    parser.add_argument("--start_instance_id", type=str, default="", help="The instance_id to start processing from")
    args = parser.parse_args()
    dataset = load_dataset(args.dataset)[args.split]  # nosec B615 - Safe: evaluation benchmark dataset
    docker_login()
    process_images(dataset, args.original_namespace, args.new_namespace, args.start_instance_id)
