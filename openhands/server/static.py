from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope


class SPAStaticFiles(StaticFiles):

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except Exception:
            return await super().get_response("index.html", scope)
