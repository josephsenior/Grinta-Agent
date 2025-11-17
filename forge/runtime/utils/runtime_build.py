"""Helpers for building Forge runtime images and managing build artifacts."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import string
import tempfile
from enum import Enum
from pathlib import Path

import docker  # type: ignore[import-untyped]
from dirhash import dirhash  # type: ignore[import-untyped]
from jinja2 import Environment, FileSystemLoader

import forge
from forge import __version__ as oh_version
from forge.core.exceptions import AgentRuntimeBuildError
from forge.core.logger import forge_logger as logger
from forge.runtime.builder import DockerRuntimeBuilder, RuntimeBuilder


class BuildFromImageType(str, Enum):
    """Enumeration of supported base image sources for runtime build."""

    BASE_IMAGE = "base_image"
    SCRATCH = "scratch"
    VERSIONED = "versioned"
    LOCK = "lock"


def get_runtime_image_repo() -> str:
    """Get the runtime image repository from environment variable.

    Returns:
        str: The runtime image repository URL.

    """
    return os.getenv("OH_RUNTIME_RUNTIME_IMAGE_REPO", "ghcr.io/all-hands-ai/runtime")


def _generate_dockerfile(
    base_image: str,
    build_from: BuildFromImageType = BuildFromImageType.SCRATCH,
    extra_deps: str | None = None,
    enable_browser: bool = True,
) -> str:
    """Generate the Dockerfile content for the runtime image based on the base image.

    Parameters:
    - base_image (str): The base image provided for the runtime image
    - build_from (BuildFromImageType): The build method for the runtime image.
    - extra_deps (str):
    - enable_browser (bool): Whether to enable browser support (install Playwright)

    Returns:
    - str: The resulting Dockerfile content

    """
    # nosec B701 - Template rendering for Dockerfile (not HTML), autoescape enabled
    env = Environment(
        loader=FileSystemLoader(
            searchpath=os.path.join(os.path.dirname(__file__), "runtime_templates"),
        ),
        autoescape=True,
    )
    template = env.get_template("Dockerfile.j2")
    return template.render(
        base_image=base_image,
        build_from_scratch=build_from == BuildFromImageType.SCRATCH,
        build_from_versioned=build_from == BuildFromImageType.VERSIONED,
        extra_deps=extra_deps if extra_deps is not None else "",
        enable_browser=enable_browser,
    )


def get_runtime_image_repo_and_tag(base_image: str) -> tuple[str, str]:
    """Retrieves the Docker repo and tag associated with the Docker image.

    Parameters:
    - base_image (str): The name of the base Docker image

    Returns:
    - tuple[str, str]: The Docker repo and tag of the Docker image

    """
    if get_runtime_image_repo() in base_image:
        logger.debug(
            "The provided image [%s] is already a valid runtime image.\nWill try to reuse it as is.",
            base_image,
        )
        if ":" not in base_image:
            base_image += ":latest"
        repo, tag = base_image.split(":")
        return (repo, tag)
    if ":" not in base_image:
        base_image += ":latest"
    [repo, tag] = base_image.split(":")
    if len(repo) > 32:
        repo_hash = hashlib.sha256(repo[:-24].encode()).hexdigest()[:8]
        repo = f"{repo_hash}_{repo[-24:]}"
    else:
        repo = repo.replace("/", "_s_")
    new_tag = f"oh_v{oh_version}_image_{repo}_tag_{tag}"
    if len(new_tag) > 128:
        new_tag = f"oh_v{oh_version}_image_{hashlib.sha256(new_tag.encode()).hexdigest()[:64]}"
        logger.warning(
            "The new tag [%s] is still too long, so we use an hash of the entire image name: %s",
            new_tag,
            new_tag,
        )
    return (get_runtime_image_repo(), new_tag)


def build_runtime_image(
    base_image: str,
    runtime_builder: RuntimeBuilder,
    platform: str | None = None,
    extra_deps: str | None = None,
    build_folder: str | None = None,
    dry_run: bool = False,
    force_rebuild: bool = False,
    extra_build_args: list[str] | None = None,
    enable_browser: bool = True,
) -> str:
    """Prepares the final docker build folder.

    If dry_run is False, it will also build the Forge runtime Docker image using the docker build folder.

    Parameters:
    - base_image (str): The name of the base Docker image to use
    - runtime_builder (RuntimeBuilder): The runtime builder to use
    - platform (str): The target platform for the build (e.g. linux/amd64, linux/arm64)
    - extra_deps (str):
    - build_folder (str): The directory to use for the build. If not provided a temporary directory will be used
    - dry_run (bool): if True, it will only ready the build folder. It will not actually build the Docker image
    - force_rebuild (bool): if True, it will create the Dockerfile which uses the base_image
    - extra_build_args (List[str]): Additional build arguments to pass to the builder
    - enable_browser (bool): Whether to enable browser support (install Playwright)

    Returns:
    - str: <image_repo>:<MD5 hash>. Where MD5 hash is the hash of the docker build folder

    See https://docs.all-hands.dev/usage/architecture/runtime for more details.

    """
    if build_folder is None:
        with tempfile.TemporaryDirectory() as temp_dir:
            return build_runtime_image_in_folder(
                base_image=base_image,
                runtime_builder=runtime_builder,
                build_folder=Path(temp_dir),
                extra_deps=extra_deps,
                dry_run=dry_run,
                force_rebuild=force_rebuild,
                platform=platform,
                extra_build_args=extra_build_args,
                enable_browser=enable_browser,
            )
    return build_runtime_image_in_folder(
        base_image=base_image,
        runtime_builder=runtime_builder,
        build_folder=Path(build_folder),
        extra_deps=extra_deps,
        dry_run=dry_run,
        force_rebuild=force_rebuild,
        platform=platform,
        extra_build_args=extra_build_args,
        enable_browser=enable_browser,
    )


def build_runtime_image_in_folder(
    base_image: str,
    runtime_builder: RuntimeBuilder,
    build_folder: Path,
    extra_deps: str | None,
    dry_run: bool,
    force_rebuild: bool,
    platform: str | None = None,
    extra_build_args: list[str] | None = None,
    enable_browser: bool = True,
) -> str:
    """Build runtime image in a specific folder.

    Args:
        base_image: The base Docker image to use.
        runtime_builder: The runtime builder to use.
        build_folder: The folder to build the image in.
        extra_deps: Additional dependencies to include.
        dry_run: Whether to perform a dry run.
        force_rebuild: Whether to force a rebuild.
        platform: Target platform for the build.
        extra_build_args: Additional build arguments.
        enable_browser: Whether to enable browser support.

    Returns:
        str: The built image name.

    """
    runtime_image_repo, _ = get_runtime_image_repo_and_tag(base_image)
    lock_tag = f"oh_v{oh_version}_{get_hash_for_lock_files(base_image, enable_browser)}"
    versioned_tag = f"oh_v{oh_version}_{get_tag_for_versioned_image(base_image)}"
    versioned_image_name = f"{runtime_image_repo}:{versioned_tag}"
    source_tag = f"{lock_tag}_{get_hash_for_source_files()}"
    hash_image_name = f"{runtime_image_repo}:{source_tag}"
    logger.info("Building image: %s", hash_image_name)
    if force_rebuild:
        logger.debug(
            "Force rebuild: [%s:%s] from scratch.",
            runtime_image_repo,
            source_tag,
        )
        prep_build_folder(
            build_folder,
            base_image,
            build_from=BuildFromImageType.SCRATCH,
            extra_deps=extra_deps,
            enable_browser=enable_browser,
        )
        if not dry_run:
            _build_sandbox_image(
                build_folder,
                runtime_builder,
                runtime_image_repo,
                source_tag,
                lock_tag,
                versioned_tag,
                platform,
                extra_build_args=extra_build_args,
            )
        return hash_image_name
    lock_image_name = f"{runtime_image_repo}:{lock_tag}"
    build_from = BuildFromImageType.SCRATCH
    if runtime_builder.image_exists(hash_image_name, False):
        logger.debug("Reusing Image [%s]", hash_image_name)
        return hash_image_name
    if runtime_builder.image_exists(lock_image_name):
        logger.debug(
            "Build [%s] from lock image [%s]",
            hash_image_name,
            lock_image_name,
        )
        build_from = BuildFromImageType.LOCK
        base_image = lock_image_name
    elif runtime_builder.image_exists(versioned_image_name):
        logger.info(
            "Build [%s] from versioned image [%s]",
            hash_image_name,
            versioned_image_name,
        )
        build_from = BuildFromImageType.VERSIONED
        base_image = versioned_image_name
    else:
        logger.debug("Build [%s] from scratch", hash_image_name)
    prep_build_folder(build_folder, base_image, build_from, extra_deps, enable_browser)
    if not dry_run:
        _build_sandbox_image(
            build_folder,
            runtime_builder,
            runtime_image_repo,
            source_tag=source_tag,
            lock_tag=lock_tag,
            versioned_tag=(
                versioned_tag if build_from == BuildFromImageType.SCRATCH else None
            ),
            platform=platform,
            extra_build_args=extra_build_args,
        )
    return hash_image_name


def prep_build_folder(
    build_folder: Path,
    base_image: str,
    build_from: BuildFromImageType,
    extra_deps: str | None,
    enable_browser: bool = True,
) -> None:
    """Prepare the build folder for runtime image construction.

    Args:
        build_folder: The folder to prepare for building.
        base_image: The base Docker image to use.
        build_from: The type of build (scratch, versioned, or lock).
        extra_deps: Additional dependencies to include.
        enable_browser: Whether to enable browser support.

    """
    FORGE_source_dir = Path(forge.__file__).parent
    project_root = FORGE_source_dir.parent
    logger.debug("Building source distribution using project root: %s", project_root)
    shutil.copytree(
        FORGE_source_dir,
        Path(build_folder, "code", "forge"),
        ignore=shutil.ignore_patterns(".*/", "__pycache__/", "*.pyc", "*.md"),
    )
    shutil.copytree(
        Path(project_root, "microagents"),
        Path(build_folder, "code", "microagents"),
    )
    for file in ["pyproject.toml", "poetry.lock"]:
        src = Path(FORGE_source_dir, file)
        if not src.exists():
            src = Path(project_root, file)
        shutil.copy2(src, Path(build_folder, "code", file))
    dockerfile_content = _generate_dockerfile(
        base_image,
        build_from=build_from,
        extra_deps=extra_deps,
        enable_browser=enable_browser,
    )
    dockerfile_path = Path(build_folder, "Dockerfile")
    with open(str(dockerfile_path), "w", encoding="utf-8") as f:
        f.write(dockerfile_content)


_ALPHABET = string.digits + string.ascii_lowercase


def truncate_hash(hash: str) -> str:
    """Convert the base16 hash to base36 and truncate at 16 characters."""
    value = int(hash, 16)
    result: list[str] = []
    while value > 0 and len(result) < 16:
        value, remainder = divmod(value, len(_ALPHABET))
        result.append(_ALPHABET[remainder])
    return "".join(result)


def get_hash_for_lock_files(base_image: str, enable_browser: bool = True) -> str:
    """Get hash for lock files based on base image and browser configuration.

    Args:
        base_image: The base Docker image name.
        enable_browser: Whether browser support is enabled.

    Returns:
        str: The hash for lock files.

    """
    FORGE_source_dir = Path(forge.__file__).parent
    sha256 = hashlib.sha256()
    sha256.update(base_image.encode())
    if not enable_browser:
        sha256.update(str(enable_browser).encode())
    for file in ["pyproject.toml", "poetry.lock"]:
        src = Path(FORGE_source_dir, file)
        if not src.exists():
            src = Path(FORGE_source_dir.parent, file)
        with open(src, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
    return truncate_hash(sha256.hexdigest())


def get_tag_for_versioned_image(base_image: str) -> str:
    """Get tag for versioned image from base image name.

    Args:
        base_image: The base Docker image name.

    Returns:
        str: The tag for versioned image.

    """
    return base_image.replace("/", "_s_").replace(":", "_t_").lower()[-96:]


def get_hash_for_source_files() -> str:
    """Get hash for source files in the Forge directory.

    Returns:
        str: The hash for source files.

    """
    FORGE_source_dir = Path(forge.__file__).parent
    dir_hash = dirhash(
        FORGE_source_dir,
        "md5",
        ignore=[".*/", "__pycache__/", "*.pyc"],
    )
    return truncate_hash(dir_hash)


def _build_sandbox_image(
    build_folder: Path,
    runtime_builder: RuntimeBuilder,
    runtime_image_repo: str,
    source_tag: str,
    lock_tag: str,
    versioned_tag: str | None,
    platform: str | None = None,
    extra_build_args: list[str] | None = None,
) -> str:
    """Build and tag the sandbox image with all available tags.

    Args:
        build_folder: The folder containing the Docker build context.
        runtime_builder: The runtime builder to use.
        runtime_image_repo: The repository for the runtime image.
        source_tag: The source tag for the image.
        lock_tag: The lock tag for the image.
        versioned_tag: The versioned tag for the image.
        platform: Target platform for the build.
        extra_build_args: Additional build arguments.

    Returns:
        str: The built image name.

    """
    names = [f"{runtime_image_repo}:{source_tag}", f"{runtime_image_repo}:{lock_tag}"]
    if versioned_tag is not None:
        names.append(f"{runtime_image_repo}:{versioned_tag}")
    names = [name for name in names if not runtime_builder.image_exists(name, False)]
    if image_name := runtime_builder.build(
        path=str(build_folder),
        tags=names,
        platform=platform,
        extra_build_args=extra_build_args,
    ):
        return image_name
    msg = f"Build failed for image {names}"
    raise AgentRuntimeBuildError(msg)


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base_image",
        type=str,
        default="nikolaik/python-nodejs:python3.12-nodejs22",
    )
    parser.add_argument("--build_folder", type=str, default=None)
    parser.add_argument("--force_rebuild", action="store_true", default=False)
    parser.add_argument("--platform", type=str, default=None)
    parser.add_argument("--enable_browser", action="store_true", default=True)
    parser.add_argument(
        "--no_enable_browser",
        dest="enable_browser",
        action="store_false",
    )
    args = parser.parse_args()
    if args.build_folder is not None:
        build_folder = args.build_folder
        assert os.path.exists(
            build_folder,
        ), f"Build folder {build_folder} does not exist"
        logger.debug(
            "Copying the source code and generating the Dockerfile in the build folder: %s",
            build_folder,
        )
        runtime_image_repo, runtime_image_tag = get_runtime_image_repo_and_tag(
            args.base_image,
        )
        logger.debug(
            "Runtime image repo: %s and runtime image tag: %s",
            runtime_image_repo,
            runtime_image_tag,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_image_hash_name = build_runtime_image(
                args.base_image,
                runtime_builder=DockerRuntimeBuilder(docker.from_env()),
                build_folder=temp_dir,
                dry_run=True,
                force_rebuild=args.force_rebuild,
                platform=args.platform,
                enable_browser=args.enable_browser,
            )
            _runtime_image_repo, runtime_image_source_tag = (
                runtime_image_hash_name.split(":")
            )
            shutil.copytree(temp_dir, build_folder, dirs_exist_ok=True)
        logger.debug(
            "Build folder [%s] is ready: %s",
            build_folder,
            os.listdir(build_folder),
        )
        with open(os.path.join(build_folder, "config.sh"), "a") as file:
            file.write(
                f"\nDOCKER_IMAGE_TAG={runtime_image_tag}\nDOCKER_IMAGE_SOURCE_TAG={runtime_image_source_tag}\n",
            )
        logger.debug(
            "`config.sh` is updated with the image repo[%s] and tags [%s, %s]",
            runtime_image_repo,
            runtime_image_tag,
            runtime_image_source_tag,
        )
        logger.debug(
            "Dockerfile, source code and config.sh are ready in %s",
            build_folder,
        )
    else:
        logger.debug("Building image in a temporary folder")
        docker_builder = DockerRuntimeBuilder(docker.from_env())
        image_name = build_runtime_image(
            args.base_image,
            docker_builder,
            platform=args.platform,
            enable_browser=args.enable_browser,
        )
        logger.debug("\nBuilt image: %s\n", image_name)
