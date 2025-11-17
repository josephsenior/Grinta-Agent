import argparse

import pytest

from forge.core.config import arg_utils


def test_get_subparser_returns_expected():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    serve = subparsers.add_parser("serve")
    cli = subparsers.add_parser("cli")
    assert arg_utils.get_subparser(parser, "serve") is serve
    assert arg_utils.get_subparser(parser, "cli") is cli


def test_get_subparser_unknown_raises():
    parser = argparse.ArgumentParser()
    parser.add_subparsers(dest="command")
    with pytest.raises(ValueError):
        arg_utils.get_subparser(parser, "missing")


def test_add_common_and_headless_arguments():
    parser = argparse.ArgumentParser()
    arg_utils.add_common_arguments(parser)
    arg_utils.add_headless_specific_arguments(parser)
    option_strings = parser._option_string_actions.keys()
    assert "--config-file" in option_strings
    assert "--max-iterations" in option_strings
    assert "--selected-repo" in option_strings


def test_add_evaluation_arguments():
    parser = argparse.ArgumentParser()
    arg_utils.add_evaluation_arguments(parser)
    option_strings = parser._option_string_actions.keys()
    assert "--eval-output-dir" in option_strings
    assert "--eval-num-workers" in option_strings


def test_get_cli_parser_contains_commands():
    parser = arg_utils.get_cli_parser()
    subparser = arg_utils.get_subparser(parser, "serve")
    assert isinstance(subparser, argparse.ArgumentParser)
    cli_parser = arg_utils.get_subparser(parser, "cli")
    args = cli_parser.parse_args(["--config-file", "custom.toml"])
    assert args.config_file == "custom.toml"


def test_get_headless_parser_has_full_argument_set():
    parser = arg_utils.get_headless_parser()
    args = parser.parse_args(
        [
            "--config-file",
            "cfg.toml",
            "--max-iterations",
            "5",
            "--max-budget-per-task",
            "10.5",
        ]
    )
    assert args.config_file == "cfg.toml"
    assert args.max_iterations == 5
    assert args.max_budget_per_task == 10.5


def test_get_evaluation_parser_combines_arguments():
    parser = arg_utils.get_evaluation_parser()
    args = parser.parse_args(
        [
            "--eval-output-dir",
            "out",
            "--eval-n-limit",
            "2",
            "--eval-num-workers",
            "3",
            "--task",
            "demo",
        ]
    )
    assert args.eval_output_dir == "out"
    assert args.eval_n_limit == 2
    assert args.task == "demo"
