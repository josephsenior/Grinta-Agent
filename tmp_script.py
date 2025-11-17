from fastapi import FastAPI
from fastapi.testclient import TestClient
from forge.server.routes import git
from forge.integrations.provider import ProviderToken, ProviderType
from forge.server.user_auth import get_access_token, get_provider_tokens, get_user_id
from forge.server.dependencies import check_session_api_key
from pydantic import SecretStr
from types import MappingProxyType

app = FastAPI()
app.include_router(git.app)


def mock_get_provider_tokens():
    return MappingProxyType(
        {ProviderType.GITHUB: ProviderToken(token=SecretStr("abc"), host="github.com")}
    )


app.dependency_overrides[get_provider_tokens] = mock_get_provider_tokens
app.dependency_overrides[get_access_token] = lambda: None
app.dependency_overrides[get_user_id] = lambda: "test"
app.dependency_overrides[check_session_api_key] = lambda: None
client = TestClient(app)
resp = client.get("/repository/test/repo/microagents")
print(resp.status_code)
print(resp.text)
