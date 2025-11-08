import hashlib
import os
import tempfile
import uuid
from importlib.metadata import version
from pathlib import Path
from unittest.mock import ANY, MagicMock, mock_open, patch
import docker
import pytest
import toml
from pytest import TempPathFactory
import forge
from forge import __version__ as oh_version
from forge.core.logger import forge_logger as logger
from forge.runtime.builder.docker import DockerRuntimeBuilder
from forge.runtime.utils.runtime_build import (
    BuildFromImageType,
    _generate_dockerfile,
    build_runtime_image,
    get_hash_for_lock_files,
    get_hash_for_source_files,
    get_runtime_image_repo,
    get_runtime_image_repo_and_tag,
    prep_build_folder,
    truncate_hash,
)

OH_VERSION = f"oh_v{oh_version}"
DEFAULT_BASE_IMAGE = "nikolaik/python-nodejs:python3.12-nodejs22"


@pytest.fixture
def temp_dir(tmp_path_factory: TempPathFactory) -> str:
    return str(tmp_path_factory.mktemp("test_runtime_build"))


@pytest.fixture
def mock_docker_client():
    mock_client = MagicMock(spec=docker.DockerClient)
    mock_client.version.return_value = {"Version": "20.10.0", "Components": [{"Name": "Engine", "Version": "20.10.0"}]}
    mock_client.images.get.return_value = MagicMock()
    return mock_client


@pytest.fixture(autouse=True)
def _patch_docker_from_env(monkeypatch, mock_docker_client):
    """Autouse fixture to ensure docker.from_env returns a mock client when.

    Docker isn't available on the test host (e.g., Windows without Docker).
    This keeps tests hermetic and CI-friendly.
    """
    monkeypatch.setattr(docker, "from_env", lambda: mock_docker_client)


@pytest.fixture(autouse=True)
def _patch_subprocess_popen(monkeypatch, encoding='utf-8'):
    """Patch subprocess.Popen used by the DockerRuntimeBuilder to simulate.

    docker buildx output so tests don't invoke the real docker binary.
    """

    class FakeStdout:

        def __init__(self, lines):
            self._lines = [line if line.endswith("\n") else line + "\n" for line in lines]
            self._index = 0

        def readline(self):
            if self._index < len(self._lines):
                line = self._lines[self._index]
                self._index += 1
                return line
            return ""

    class FakePopen:

        def __init__(self, args, stdout=None, stderr=None, universal_newlines=None, bufsize=None, **kwargs):
            self.args = args
            self.stdout = FakeStdout(["Step 1: fake build output", "Step 2: done"])
            self.returncode = 0

        def wait(self):
            return 0

        def poll(self):
            return self.returncode

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def communicate(self, input=None, timeout=None):
            output = "".join(self.stdout._lines)
            return (output, "")

        def kill(self):
            return None

    monkeypatch.setattr("subprocess.Popen", FakePopen)


@pytest.fixture
def docker_runtime_builder(mock_docker_client):
    """Return a DockerRuntimeBuilder using a real docker client when available,.

    otherwise fall back to the mock_docker_client so tests don't require a
    running Docker daemon (useful on CI and Windows without Docker).
    """
    try:
        client = docker.from_env()
    except Exception:
        client = mock_docker_client
    return DockerRuntimeBuilder(client)


def _check_source_code_in_dir(temp_dir):
    code_dir = os.path.join(temp_dir, "code")
    assert os.path.exists(code_dir)
    assert os.path.isdir(code_dir)
    assert os.path.exists(os.path.join(code_dir, "pyproject.toml"))
    assert set(os.listdir(code_dir)) == {"forge", "pyproject.toml", "poetry.lock"}
    assert os.path.exists(os.path.join(code_dir, "forge"))
    assert os.path.isdir(os.path.join(code_dir, "forge"))
    with open(os.path.join(code_dir, "pyproject.toml"), "r") as f:
        pyproject = toml.load(f)
    _pyproject_version = pyproject["tool"]["poetry"]["version"]
    assert _pyproject_version == version("Forge-ai")


def test_prep_build_folder(temp_dir):
    shutil_mock = MagicMock()
    with patch(f"{prep_build_folder.__module__}.shutil", shutil_mock):
        prep_build_folder(
            temp_dir, base_image=DEFAULT_BASE_IMAGE, build_from=BuildFromImageType.SCRATCH, extra_deps=None
        )
    assert shutil_mock.copytree.call_count == 2
    assert shutil_mock.copy2.call_count == 2
    dockerfile_path = os.path.join(temp_dir, "Dockerfile")
    assert os.path.exists(dockerfile_path)
    assert os.path.isfile(dockerfile_path)


def test_get_hash_for_lock_files():
    with patch("builtins.open", mock_open(read_data="mock-data".encode(encoding='utf-8'))):
        hash = get_hash_for_lock_files("some_base_image", enable_browser=True)
        sha256 = hashlib.sha256()
        sha256.update("some_base_image".encode())
        for _ in range(2):
            sha256.update("mock-data".encode())
        assert hash == truncate_hash(sha256.hexdigest())


def test_get_hash_for_lock_files_different_enable_browser():
    with patch("builtins.open", mock_open(read_data="mock-data".encode(encoding='utf-8'))):
        hash_true = get_hash_for_lock_files("some_base_image", enable_browser=True)
        hash_false = get_hash_for_lock_files("some_base_image", enable_browser=False)
        sha256_true = hashlib.sha256()
        sha256_true.update("some_base_image".encode())
        for _ in range(2):
            sha256_true.update("mock-data".encode())
        expected_hash_true = truncate_hash(sha256_true.hexdigest())
        sha256_false = hashlib.sha256()
        sha256_false.update("some_base_image".encode())
        sha256_false.update("False".encode())
        for _ in range(2):
            sha256_false.update("mock-data".encode())
        expected_hash_false = truncate_hash(sha256_false.hexdigest())
        assert hash_true == expected_hash_true
        assert hash_false == expected_hash_false
        assert hash_true != hash_false


def test_get_hash_for_source_files():
    dirhash_mock = MagicMock()
    dirhash_mock.return_value = "1f69bd20d68d9e3874d5bf7f7459709b"
    with patch(f"{get_hash_for_source_files.__module__}.dirhash", dirhash_mock):
        result = get_hash_for_source_files()
        assert result == truncate_hash(dirhash_mock.return_value)
        dirhash_mock.assert_called_once_with(
            Path(forge.__file__).parent, "md5", ignore=[".*/", "__pycache__/", "*.pyc"]
        )


def test_generate_dockerfile_build_from_scratch():
    base_image = "debian:11"
    dockerfile_content = _generate_dockerfile(base_image, build_from=BuildFromImageType.SCRATCH)
    assert base_image in dockerfile_content
    assert "apt-get update" in dockerfile_content
    assert "wget curl" in dockerfile_content
    assert "poetry" in dockerfile_content and "-c conda-forge" in dockerfile_content
    assert "python=3.12" in dockerfile_content
    assert "COPY --chown=Forge:Forge ./code/Forge /Forge/code/Forge" in dockerfile_content
    assert "/Forge/micromamba/bin/micromamba run -n Forge poetry install" in dockerfile_content


def test_generate_dockerfile_build_from_lock():
    base_image = "debian:11"
    dockerfile_content = _generate_dockerfile(base_image, build_from=BuildFromImageType.LOCK)
    assert "wget curl sudo apt-utils git" not in dockerfile_content
    assert "-c conda-forge" not in dockerfile_content
    assert "python=3.12" not in dockerfile_content
    assert "https://micro.mamba.pm/install.sh" not in dockerfile_content
    assert "poetry install" not in dockerfile_content
    assert "COPY --chown=Forge:Forge ./code/Forge /Forge/code/Forge" in dockerfile_content


def test_generate_dockerfile_build_from_versioned():
    base_image = "debian:11"
    dockerfile_content = _generate_dockerfile(base_image, build_from=BuildFromImageType.VERSIONED)
    assert "wget curl sudo apt-utils git" not in dockerfile_content
    assert "-c conda-forge" not in dockerfile_content
    assert "python=3.12" not in dockerfile_content
    assert "https://micro.mamba.pm/install.sh" not in dockerfile_content
    assert "poetry install" in dockerfile_content
    assert "COPY --chown=Forge:Forge ./code/Forge /Forge/code/Forge" in dockerfile_content


def test_get_runtime_image_repo_and_tag_eventstream():
    base_image = "debian:11"
    img_repo, img_tag = get_runtime_image_repo_and_tag(base_image)
    assert img_repo == f"{get_runtime_image_repo()}" and img_tag == f"{OH_VERSION}_image_debian_tag_11"
    img_repo, img_tag = get_runtime_image_repo_and_tag(DEFAULT_BASE_IMAGE)
    assert (
        img_repo
        == f"{
            get_runtime_image_repo()}"
        and img_tag == f"{OH_VERSION}_image_nikolaik_s_python-nodejs_tag_python3.12-nodejs22"
    )
    base_image = "ubuntu"
    img_repo, img_tag = get_runtime_image_repo_and_tag(base_image)
    assert img_repo == f"{get_runtime_image_repo()}" and img_tag == f"{OH_VERSION}_image_ubuntu_tag_latest"


def test_build_runtime_image_from_scratch():
    base_image = "debian:11"
    mock_lock_hash = MagicMock()
    mock_lock_hash.return_value = "mock-lock-tag"
    mock_versioned_tag = MagicMock()
    mock_versioned_tag.return_value = "mock-versioned-tag"
    mock_source_hash = MagicMock()
    mock_source_hash.return_value = "mock-source-tag"
    mock_runtime_builder = MagicMock()
    mock_runtime_builder.image_exists.return_value = False
    mock_runtime_builder.build.return_value = f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"
    mock_prep_build_folder = MagicMock()
    mod = build_runtime_image.__module__
    with patch(f"{mod}.get_hash_for_lock_files", mock_lock_hash), patch(
        f"{mod}.get_hash_for_source_files", mock_source_hash
    ), patch(f"{mod}.get_tag_for_versioned_image", mock_versioned_tag), patch(
        f"{build_runtime_image.__module__}.prep_build_folder", mock_prep_build_folder
    ):
        image_name = build_runtime_image(base_image, mock_runtime_builder)
        mock_runtime_builder.build.assert_called_once_with(
            path=ANY,
            tags=[
                f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag",
                f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag",
                f"{get_runtime_image_repo()}:{OH_VERSION}_mock-versioned-tag",
            ],
            platform=None,
            extra_build_args=None,
        )
        assert image_name == f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"
        mock_prep_build_folder.assert_called_once_with(ANY, base_image, BuildFromImageType.SCRATCH, None, True)


def test_build_runtime_image_exact_hash_exist():
    base_image = "debian:11"
    mock_lock_hash = MagicMock()
    mock_lock_hash.return_value = "mock-lock-tag"
    mock_source_hash = MagicMock()
    mock_source_hash.return_value = "mock-source-tag"
    mock_versioned_tag = MagicMock()
    mock_versioned_tag.return_value = "mock-versioned-tag"
    mock_runtime_builder = MagicMock()
    mock_runtime_builder.image_exists.return_value = True
    mock_runtime_builder.build.return_value = f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"
    mock_prep_build_folder = MagicMock()
    mod = build_runtime_image.__module__
    with patch(f"{mod}.get_hash_for_lock_files", mock_lock_hash), patch(
        f"{mod}.get_hash_for_source_files", mock_source_hash
    ), patch(f"{mod}.get_tag_for_versioned_image", mock_versioned_tag), patch(
        f"{build_runtime_image.__module__}.prep_build_folder", mock_prep_build_folder
    ):
        image_name = build_runtime_image(base_image, mock_runtime_builder)
        assert image_name == f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"
        mock_runtime_builder.build.assert_not_called()
        mock_prep_build_folder.assert_not_called()


def test_build_runtime_image_exact_hash_not_exist_and_lock_exist():
    base_image = "debian:11"
    mock_lock_hash = MagicMock()
    mock_lock_hash.return_value = "mock-lock-tag"
    mock_source_hash = MagicMock()
    mock_source_hash.return_value = "mock-source-tag"
    mock_versioned_tag = MagicMock()
    mock_versioned_tag.return_value = "mock-versioned-tag"
    mock_runtime_builder = MagicMock()

    def image_exists_side_effect(image_name, *args):
        if "mock-lock-tag_mock-source-tag" in image_name:
            return False
        elif "mock-lock-tag" in image_name:
            return True
        elif "mock-versioned-tag" in image_name:
            return False
        else:
            raise ValueError(f"Unexpected image name: {image_name}")

    mock_runtime_builder.image_exists.side_effect = image_exists_side_effect
    mock_runtime_builder.build.return_value = f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"
    mock_prep_build_folder = MagicMock()
    mod = build_runtime_image.__module__
    with patch(f"{mod}.get_hash_for_lock_files", mock_lock_hash), patch(
        f"{mod}.get_hash_for_source_files", mock_source_hash
    ), patch(f"{mod}.get_tag_for_versioned_image", mock_versioned_tag), patch(
        f"{build_runtime_image.__module__}.prep_build_folder", mock_prep_build_folder
    ):
        image_name = build_runtime_image(base_image, mock_runtime_builder)
        assert image_name == f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"
        mock_runtime_builder.build.assert_called_once_with(
            path=ANY,
            tags=[f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"],
            platform=None,
            extra_build_args=None,
        )
        mock_prep_build_folder.assert_called_once_with(
            ANY, f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag", BuildFromImageType.LOCK, None, True
        )


def test_build_runtime_image_exact_hash_not_exist_and_lock_not_exist_and_versioned_exist():
    base_image = "debian:11"
    mock_lock_hash = MagicMock()
    mock_lock_hash.return_value = "mock-lock-tag"
    mock_source_hash = MagicMock()
    mock_source_hash.return_value = "mock-source-tag"
    mock_versioned_tag = MagicMock()
    mock_versioned_tag.return_value = "mock-versioned-tag"
    mock_runtime_builder = MagicMock()

    def image_exists_side_effect(image_name, *args):
        if "mock-lock-tag_mock-source-tag" in image_name:
            return False
        elif "mock-lock-tag" in image_name:
            return False
        elif "mock-versioned-tag" in image_name:
            return True
        else:
            raise ValueError(f"Unexpected image name: {image_name}")

    mock_runtime_builder.image_exists.side_effect = image_exists_side_effect
    mock_runtime_builder.build.return_value = f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"
    mock_prep_build_folder = MagicMock()
    mod = build_runtime_image.__module__
    with patch(f"{mod}.get_hash_for_lock_files", mock_lock_hash), patch(
        f"{mod}.get_hash_for_source_files", mock_source_hash
    ), patch(f"{mod}.get_tag_for_versioned_image", mock_versioned_tag), patch(
        f"{build_runtime_image.__module__}.prep_build_folder", mock_prep_build_folder
    ):
        image_name = build_runtime_image(base_image, mock_runtime_builder)
        assert image_name == f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag"
        mock_runtime_builder.build.assert_called_once_with(
            path=ANY,
            tags=[
                f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag_mock-source-tag",
                f"{get_runtime_image_repo()}:{OH_VERSION}_mock-lock-tag",
            ],
            platform=None,
            extra_build_args=None,
        )
        mock_prep_build_folder.assert_called_once_with(
            ANY, f"{get_runtime_image_repo()}:{OH_VERSION}_mock-versioned-tag", BuildFromImageType.VERSIONED, None, True
        )


def test_output_build_progress(docker_runtime_builder):
    layers = {}
    docker_runtime_builder._output_build_progress(
        {"id": "layer1", "status": "Downloading", "progressDetail": {"current": 50, "total": 100}}, layers, 0
    )
    assert layers["layer1"]["status"] == "Downloading"
    assert layers["layer1"]["progress"] == ""
    assert layers["layer1"]["last_logged"] == 50.0


@pytest.fixture(scope="function")
def live_docker_image():
    client = docker.from_env()
    unique_id = str(uuid.uuid4())[:8]
    unique_prefix = f"test_image_{unique_id}"
    dockerfile_content = f'\n    # syntax=docker/dockerfile:1.4\n    FROM {DEFAULT_BASE_IMAGE} AS base\n    RUN apt-get update && apt-get install -y wget curl sudo apt-utils\n\n    FROM base AS intermediate\n    RUN mkdir -p /Forge\n\n    FROM intermediate AS final\n    RUN echo "Hello, Forge!" > /Forge/hello.txt\n    '
    with tempfile.TemporaryDirectory() as temp_dir:
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w", encoding='utf-8') as f:
            f.write(dockerfile_content)
        try:
            image, logs = client.images.build(
                path=temp_dir,
                tag=f"{unique_prefix}:final",
                buildargs={"DOCKER_BUILDKIT": "1"},
                labels={"test": "true"},
                rm=True,
                forcerm=True,
            )
            client.api.tag(image.id, unique_prefix, "base")
            client.api.tag(image.id, unique_prefix, "intermediate")
            all_tags = [f"{unique_prefix}:final", f"{unique_prefix}:base", f"{unique_prefix}:intermediate"]
            print(f"\nImage ID: {image.id}")
            print(f"Image tags: {all_tags}\n")
            yield image
        finally:
            for tag in all_tags:
                try:
                    client.images.remove(tag, force=True)
                    print(f"Removed image: {tag}")
                except Exception as e:
                    print(f"Error removing image {tag}: {str(e)}")


def test_init(docker_runtime_builder):
    assert isinstance(docker_runtime_builder.docker_client, docker.DockerClient)
    assert docker_runtime_builder.rolling_logger.max_lines == 10
    assert docker_runtime_builder.rolling_logger.log_lines == [""] * 10


def test_build_image_from_scratch(docker_runtime_builder, tmp_path):
    context_path = str(tmp_path)
    tags = ["test_build:latest"]
    with open(os.path.join(context_path, "Dockerfile"), "w") as f:
        f.write('FROM php:latest\nCMD ["sh", "-c", "echo \'Hello, World!\'"]\n')
    built_image_name = None
    container = None
    client = docker.from_env()
    try:
        built_image_name = docker_runtime_builder.build(context_path, tags, use_local_cache=False)
        assert built_image_name == f"{tags[0]}"
        image = client.images.get(tags[0])
        assert image is not None
    except docker.errors.ImageNotFound:
        pytest.fail("test_build_image_from_scratch: test image not found!")
    except Exception as e:
        pytest.fail(f"test_build_image_from_scratch: Build failed with error: {str(e)}")
    finally:
        if container:
            try:
                container.remove(force=True)
                logger.info("Removed test container: `%s`", container.id)
            except Exception as e:
                logger.warning("Failed to remove test container `%s`: %s", container.id, str(e))
        if built_image_name:
            try:
                client.images.remove(built_image_name, force=True)
                logger.info("Removed test image: `%s`", built_image_name)
            except Exception as e:
                logger.warning("Failed to remove test image `%s`: %s", built_image_name, str(e))
        else:
            logger.warning("No image was built, so no image cleanup was necessary.")


def _format_size_to_gb(bytes_size):
    """Convert bytes to gigabytes with two decimal places."""
    return round(bytes_size / 1024**3, 2)


def test_list_dangling_images():
    client = docker.from_env()
    dangling_images = client.images.list(filters={"dangling": True})
    if dangling_images and len(dangling_images) > 0:
        for image in dangling_images:
            if "Size" in image.attrs and isinstance(image.attrs["Size"], int):
                size_gb = _format_size_to_gb(image.attrs["Size"])
                logger.info("Dangling image: %s, Size: %s GB", image.tags, size_gb)
            else:
                logger.info("Dangling image: %s, Size: n/a", image.tags)
    else:
        logger.info("No dangling images found")


def test_build_image_from_repo(docker_runtime_builder, tmp_path):
    context_path = str(tmp_path)
    tags = ["alpine:latest"]
    with open(os.path.join(context_path, "Dockerfile"), "w") as f:
        f.write(f"""FROM {DEFAULT_BASE_IMAGE}\nCMD ["sh", "-c", "echo 'Hello, World!'"]\n""")
    built_image_name = None
    container = None
    client = docker.from_env()
    try:
        built_image_name = docker_runtime_builder.build(context_path, tags, use_local_cache=False)
        assert built_image_name == f"{tags[0]}"
        image = client.images.get(tags[0])
        assert image is not None
    except docker.errors.ImageNotFound:
        pytest.fail("test_build_image_from_repo: test image not found!")
    finally:
        if container:
            try:
                container.remove(force=True)
                logger.info("Removed test container: `%s`", container.id)
            except Exception as e:
                logger.warning("Failed to remove test container `%s`: %s", container.id, str(e))
        if built_image_name:
            try:
                client.images.remove(built_image_name, force=True)
                logger.info("Removed test image: `%s`", built_image_name)
            except Exception as e:
                logger.warning("Failed to remove test image `%s`: %s", built_image_name, str(e))
        else:
            logger.warning("No image was built, so no image cleanup was necessary.")


def test_image_exists_local(docker_runtime_builder):
    mock_client = MagicMock()
    mock_client.version.return_value = {"Version": "20.10.0", "Components": [{"Name": "Engine", "Version": "20.10.0"}]}
    builder = DockerRuntimeBuilder(mock_client)
    image_name = "existing-local:image"
    assert builder.image_exists(image_name)


def test_image_exists_not_found():
    mock_client = MagicMock()
    mock_client.version.return_value = {"Version": "20.10.0", "Components": [{"Name": "Engine", "Version": "20.10.0"}]}
    mock_client.images.get.side_effect = docker.errors.ImageNotFound("He doesn't like you!")
    mock_client.api.pull.side_effect = docker.errors.ImageNotFound("I don't like you either!")
    builder = DockerRuntimeBuilder(mock_client)
    assert not builder.image_exists("nonexistent:image")
    mock_client.images.get.assert_called_once_with("nonexistent:image")
    mock_client.api.pull.assert_called_once_with("nonexistent", tag="image", stream=True, decode=True)


def test_truncate_hash():
    truncated = truncate_hash("b08f254d76b1c6a7ad924708c0032251")
    assert truncated == "pma2wc71uq3c9a85"
    truncated = truncate_hash("102aecc0cea025253c0278f54ebef078")
    assert truncated == "4titk6gquia3taj5"
