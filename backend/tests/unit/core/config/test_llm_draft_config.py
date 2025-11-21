import pathlib
import pytest
from forge.core.config import ForgeConfig
from forge.core.config.utils import load_from_toml


@pytest.fixture
def config_toml_without_draft_editor(tmp_path: pathlib.Path) -> str:
    """This fixture provides a TOML config that DOES NOT contain [llm.draft_editor].

    We'll use it to verify that the draft_editor LLM is not present in the config.
    """
    toml_content = '\n[core]\nworkspace_base = "./workspace"\n\n[llm]\nmodel = "base-model"\napi_key = "base-api-key"\n\n[llm.custom1]\nmodel = "custom-model-1"\napi_key = "custom-api-key-1"\n    '
    toml_file = tmp_path / "no_draft_editor.toml"
    toml_file.write_text(toml_content)
    return str(toml_file)


@pytest.fixture
def config_toml_with_draft_editor(tmp_path: pathlib.Path) -> str:
    """This fixture provides a TOML config that DOES contain [llm.draft_editor].

    We'll use it to verify that the draft_editor LLM is loaded as any other custom LLM.
    """
    toml_content = '\n[core]\nworkspace_base = "./workspace"\n\n[llm]\nmodel = "base-model"\napi_key = "base-api-key"\nnum_retries = 7\n\n[llm.draft_editor]\nmodel = "draft-model"\napi_key = "draft-api-key"\n\n[llm.custom2]\nmodel = "custom-model-2"\napi_key = "custom-api-key-2"\n    '
    toml_file = tmp_path / "yes_draft_editor.toml"
    toml_file.write_text(toml_content)
    return str(toml_file)


def test_no_draft_editor_in_config(config_toml_without_draft_editor):
    """Test that draft_editor is simply not present if not declared in the TOML.

    Previously, we tested fallback behavior. Now, it's simplified to not exist at all.
    This docstring remains to illustrate that the old fallback logic is removed.
    """
    config = ForgeConfig()
    load_from_toml(config, config_toml_without_draft_editor)
    assert "draft_editor" not in config.llms


def test_draft_editor_as_named_llm(config_toml_with_draft_editor):
    """Test that draft_editor is loaded if declared in the TOML under [llm.draft_editor].

    This docstring references the simpler approach: if it exists, it's just another named LLM.
    """
    config = ForgeConfig()
    load_from_toml(config, config_toml_with_draft_editor)
    assert "draft_editor" in config.llms
    draft_llm = config.get_llm_config("draft_editor")
    assert draft_llm is not None
    assert draft_llm.model == "draft-model"
    assert draft_llm.api_key.get_secret_value() == "draft-api-key"


def test_draft_editor_fallback(config_toml_with_draft_editor):
    """Test that the draft_editor config does pick up fallbacks.

    normally set in LLMConfig class and from generic LLM.

    We expect the 'draft_editor' LLM to behave just like any custom LLM would.
    """
    config = ForgeConfig()
    load_from_toml(config, config_toml_with_draft_editor)
    draft_editor_config = config.get_llm_config("draft_editor")
    assert draft_editor_config.num_retries == 7
