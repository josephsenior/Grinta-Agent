import os

from openai import OpenAI


def _get_openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", os.getenv("SANDBOX_ENV_OPENAI_API_KEY", ""))


def _get_openai_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def _get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o")


def _get_max_token() -> int:
    return int(os.getenv("MAX_TOKEN", "500"))


def _get_openai_client() -> OpenAI:
    return OpenAI(api_key=_get_openai_api_key(), base_url=_get_openai_base_url())
