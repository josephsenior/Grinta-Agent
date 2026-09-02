from evaluation.deepswe.pier_compat import codex_npm_install_args


def test_codex_install_includes_explicit_linux_binary_alias() -> None:
    args = codex_npm_install_args('0.150.1')

    assert '@openai/codex@0.150.1' in args
    assert '@openai/codex-linux-x64@npm:@openai/codex@0.150.1-linux-x64' in args
