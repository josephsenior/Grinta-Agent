#!/usr/bin/env python3
"""Compile Protocol Buffer definitions to Python gRPC stubs.

This script generates Python gRPC service stubs and message classes from
.proto files in forge/services/protos/.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def find_proto_files(proto_dir: Path) -> list[Path]:
    """Find all .proto files in the given directory."""
    return list(proto_dir.glob("*.proto"))


def compile_proto(proto_file: Path, output_dir: Path, include_dirs: list[Path]) -> None:
    """Compile a single .proto file to Python gRPC stubs."""
    args = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        f"--pyi_out={output_dir}",
    ]
    for include_dir in include_dirs:
        args.append(f"--proto_path={include_dir}")
    args.append(str(proto_file))

    print(f"Compiling {proto_file.name}...")
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Error compiling {proto_file.name}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def fix_grpc_relative_imports(output_dir: Path) -> None:
    """Ensure generated *_pb2_grpc.py files use package-relative imports.

    grpc_tools generates statements like `import foo_pb2 as foo__pb2`, which fails
    when the modules live inside a package. Rewriting them to
    `from . import foo_pb2 as foo__pb2` keeps imports package-scoped.
    """

    pattern = re.compile(r"^import (\w+_pb2) as (\w+)", re.MULTILINE)

    for file_path in output_dir.glob("*_pb2_grpc.py"):
        contents = file_path.read_text()
        rewritten = pattern.sub(r"from . import \1 as \2", contents)
        if rewritten != contents:
            file_path.write_text(rewritten)


def main() -> None:
    """Main entry point for proto compilation."""
    parser = argparse.ArgumentParser(description="Compile Protocol Buffer definitions")
    parser.add_argument(
        "--proto-dir",
        type=Path,
        default=Path(__file__).parent.parent / "forge" / "services" / "protos",
        help="Directory containing .proto files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "forge" / "services" / "generated",
        help="Output directory for generated Python files",
    )
    parser.add_argument(
        "--include-dirs",
        type=str,
        nargs="+",
        default=[],
        help="Additional include directories for proto imports",
    )
    args = parser.parse_args()

    proto_dir = args.proto_dir.resolve()
    output_dir = args.output_dir.resolve()
    include_dirs = [proto_dir] + [Path(d).resolve() for d in args.include_dirs]

    if not proto_dir.exists():
        print(f"Proto directory does not exist: {proto_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Add standard protobuf includes
    try:
        import google.protobuf
        proto_lib_path = Path(google.protobuf.__file__).parent.parent
        include_dirs.append(proto_lib_path / "include")
    except ImportError:
        pass

    proto_files = find_proto_files(proto_dir)
    if not proto_files:
        print(f"No .proto files found in {proto_dir}", file=sys.stderr)
        sys.exit(1)

    for proto_file in proto_files:
        compile_proto(proto_file, output_dir, include_dirs)

    fix_grpc_relative_imports(output_dir)

    # Create __init__.py in output directory
    init_file = output_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Generated gRPC service stubs and message classes."""\n')

    print(f"Successfully compiled {len(proto_files)} proto file(s) to {output_dir}")


if __name__ == "__main__":
    main()

