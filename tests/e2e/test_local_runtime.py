import os
import shutil
import subprocess
import tempfile


def test_headless_mode_with_dummy_agent_no_browser():
    """E2E test: build a docker image from python:3.13, install Forge from source,.

    and run a local runtime task in headless mode.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    dockerfile = '\n    FROM python:3.13-slim\n    WORKDIR /src\n    RUN apt-get update && apt-get install -y git build-essential tmux\n    COPY . /src\n    RUN pip install --upgrade pip setuptools wheel\n    RUN pip install .\n    ENV PYTHONUNBUFFERED=1\n    ENV RUNTIME=local\n    ENV RUN_AS_Forge=false\n    ENV ENABLE_BROWSER=false\n    ENV AGENT_ENABLE_BROWSING=false\n    ENV SKIP_DEPENDENCY_CHECK=1\n    CMD ["python", "-m", "forge.core.main", "-c", "DummyAgent", "-t", "Hello world"]\n    '
    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_path = os.path.join(tmpdir, "Dockerfile")
        with open(dockerfile_path, "w", encoding='utf-8') as f:
            f.write(dockerfile)
        build_context = os.path.join(tmpdir, "context")
        shutil.copytree(repo_root, build_context, dirs_exist_ok=True)
        image_tag = "Forge-e2e-local-runtime-test"
        build_cmd = ["docker", "build", "-t", image_tag, "-f", dockerfile_path, build_context]
        run_cmd = ["docker", "run", "--rm", image_tag]
        build_proc = subprocess.run(build_cmd, capture_output=True, text=True)
        print("Docker build stdout:", build_proc.stdout)
        print("Docker build stderr:", build_proc.stderr)
        assert build_proc.returncode == 0, "Docker build failed"
        run_proc = subprocess.run(run_cmd, capture_output=True, text=True)
        print("Docker run stdout:", run_proc.stdout)
        print("Docker run stderr:", run_proc.stderr)
        assert run_proc.returncode == 0, f"Docker run failed with code {run_proc.returncode}"
        assert "Warning: Observation mismatch" not in run_proc.stdout
