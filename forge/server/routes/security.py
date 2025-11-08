"""Proxy routes that forward requests to conversation-scoped security analyzers."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from forge.server.dependencies import get_dependencies
from forge.server.session.conversation import ServerConversation
from forge.server.utils import get_conversation

app = APIRouter(prefix="/api/conversations/{conversation_id}/security", dependencies=get_dependencies())


@app.route("/security/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def security_api(request: Request, conversation: ServerConversation = Depends(get_conversation)) -> Response:
    r"""Catch-all proxy route for security analyzer API requests.

    Routes all HTTP requests (GET, POST, PUT, DELETE) for the security
    analyzer to the active SecurityAnalyzer instance, which handles the
    actual processing and responds accordingly.

    Args:
        request: The incoming FastAPI request object containing:
            - method: HTTP method (GET, POST, PUT, DELETE)
            - url/path: Request path within the security analyzer scope
            - headers: Request headers including authentication
            - body: Request body (for POST/PUT requests)
        conversation: Injected dependency providing:
            - security_analyzer: Active SecurityAnalyzer instance
            - Other conversation context and runtime info

    Returns:
        Response: The response object from the security analyzer's
            handle_api_request() method, preserving status code, headers,
            and body from the security analyzer's response.

    Raises:
        HTTPException: 404 Not Found if the security_analyzer is not
            initialized for the current conversation session.

    Examples:
        >>> curl -X GET http://localhost:3000/api/conversations/abc123/security/issues
        # Proxied to security_analyzer.handle_api_request(request)

        >>> curl -X POST http://localhost:3000/api/conversations/abc123/security/analyze \\
        ...     -d '{"files": ["src/main.py"]}'
        # Proxied to security analyzer

    """
    if not conversation.security_analyzer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security analyzer not initialized")
    return await conversation.security_analyzer.handle_api_request(request)
