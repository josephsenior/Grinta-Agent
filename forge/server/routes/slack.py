"""Slack integration routes for forge."""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Any, Awaitable, Callable, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status, FastAPI
from fastapi.responses import JSONResponse, Response

from forge.core.logger import forge_logger as logger
from forge.events.action import AgentThinkAction, CmdRunAction, MessageAction
from forge.events.observation import (
    AgentStateChangedObservation,
    CmdOutputObservation,
)
from forge.integrations.slack_client import SLACK_SDK_AVAILABLE, SlackClient
from forge.integrations.provider import PROVIDER_TOKEN_TYPE
from forge.server.routes.manage_conversations import (
    InitSessionRequest,
    new_conversation,
)
from forge.server.shared import config
from forge.storage.data_models.slack_integration import (
    SlackConversationLink,
    SlackOutgoingMessage,
    SlackUserLink,
    SlackWorkspace,
)
from forge.storage.slack_store import SlackStore

if TYPE_CHECKING:
    from forge.events.event import Event

app = APIRouter()

# Track active Slack → Forge conversation streams
_slack_event_listeners: dict[str, tuple[SlackClient, str, str]] = {}  # conversation_id → (client, channel, thread_ts)

# Backward compatibility for tests expecting FORGE_config
FORGE_config = config

_EMPTY_PROVIDER_TOKENS: PROVIDER_TOKEN_TYPE = cast(PROVIDER_TOKEN_TYPE, MappingProxyType({}))


def create_slack_event_callback(
    client: SlackClient,
    channel_id: str,
    thread_ts: str,
    conversation_id: str,
) -> Callable[["Event"], Awaitable[None]]:
    """Create event callback to stream Forge events to Slack.

    Args:
        client: Slack client
        channel_id: Slack channel ID
        thread_ts: Slack thread timestamp
        conversation_id: Forge conversation ID

    Returns:
        Callback function for event streaming

    """

    async def callback(event: Event) -> None:
        """Stream Forge events to Slack thread."""
        try:
            # Format different event types for Slack
            if isinstance(event, AgentThinkAction):
                # Agent is thinking
                text = f":thought_balloon: *Thinking:* {event.thought}"
                client.post_message(
                    SlackOutgoingMessage(
                        channel=channel_id,
                        text=text,
                        thread_ts=thread_ts,
                        blocks=None,
                    ),
                )

            elif isinstance(event, CmdRunAction):
                # Agent is running a command
                code_block = client.format_code_block(event.command, "bash")
                text = f":computer: *Running command:*\n{code_block}"
                client.post_message(
                    SlackOutgoingMessage(
                        channel=channel_id,
                        text=text,
                        thread_ts=thread_ts,
                        blocks=None,
                    ),
                )

            elif isinstance(event, CmdOutputObservation):
                # Command output
                emoji = ":white_check_mark:" if event.exit_code == 0 else ":x:"

                output = event.content[:500]  # Limit output length
                if len(event.content) > 500:
                    output += "\n... (output truncated)"

                code_block = client.format_code_block(output)
                text = f"{emoji} *Output:*\n{code_block}"
                client.post_message(
                    SlackOutgoingMessage(
                        channel=channel_id,
                        text=text,
                        thread_ts=thread_ts,
                        blocks=None,
                    ),
                )

            elif isinstance(event, MessageAction):
                # Agent message
                text = f":speech_balloon: *Agent:* {event.content}"
                client.post_message(
                    SlackOutgoingMessage(
                        channel=channel_id,
                        text=text,
                        thread_ts=thread_ts,
                        blocks=None,
                    ),
                )

            elif isinstance(event, AgentStateChangedObservation):
                # Agent state changed
                from forge.core.schema.agent import AgentState

                if event.agent_state == AgentState.FINISHED:
                    text = ":tada: *Task completed!*"
                elif event.agent_state == AgentState.ERROR:
                    text = ":warning: *Task encountered an error*"
                elif event.agent_state == AgentState.RUNNING:
                    text = ":runner: *Agent started working...*"
                else:
                    return  # Don't spam for other states

                client.post_message(
                    SlackOutgoingMessage(
                        channel=channel_id,
                        text=text,
                        thread_ts=thread_ts,
                        blocks=None,
                    ),
                )

        except Exception as e:
            logger.error(f"Failed to stream event to Slack: {e}")

    return callback


def get_slack_store() -> SlackStore:
    """Get Slack store dependency."""
    return SlackStore(FORGE_config)


def _resolve_slack_store() -> SlackStore:
    """Indirection for dependency injection to allow runtime patching in tests."""
    return get_slack_store()


async def verify_slack_signature(request: Request, slack_signing_secret: str | None) -> bool:
    """Verify Slack request signature.

    Args:
        request: FastAPI request
        slack_signing_secret: Slack signing secret

    Returns:
        True if signature is valid, False otherwise

    """
    if not slack_signing_secret:
        logger.warning(
            "Slack signing secret not configured, skipping signature verification",
        )
        return True

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not timestamp or not signature:
        return False

    # Check if request is too old (replay attack protection)
    if abs(time.time() - int(timestamp)) > 60 * 5:  # 5 minutes
        logger.warning("Slack request timestamp too old")
        return False

    # Verify signature
    body_bytes = await request.body()
    sig_basestring = f"v0:{timestamp}:{body_bytes.decode('utf-8')}"  # nosec B324
    my_signature = (
        "v0="
        + hmac.new(
            slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(my_signature, signature)


@app.get("/install")
async def slack_install(
    user_id: str,
    redirect_url: str | None = None,
    slack_store: SlackStore = Depends(_resolve_slack_store),
) -> JSONResponse:
    """Generate Slack OAuth install URL.

    Args:
        user_id: Forge user ID
        redirect_url: URL to redirect after OAuth (optional)
        slack_store: Slack store

    Returns:
        OAuth URL to redirect user to

    """
    if not FORGE_config.SLACK_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Slack integration not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET.",
        )

    # Generate state for OAuth verification
    state = slack_store.generate_oauth_state(user_id, redirect_url)

    # Build Slack OAuth URL
    scopes = [
        "app_mentions:read",
        "channels:history",
        "chat:write",
        "groups:history",
        "im:history",
        "mpim:history",
        "users:read",
    ]
    user_scopes: list[str] = []
    install_url = (
        "https://slack.com/oauth/v2/authorize"
        f"?client_id={FORGE_config.SLACK_CLIENT_ID}"
        f"&scope={' '.join(scopes)}"
        f"&user_scope={' '.join(user_scopes)}"
        f"&state={state}"
    )

    return JSONResponse({"url": install_url})


@app.get("/callback")
async def slack_oauth_callback(
    state: str,
    code: str | None = None,
    error: str | None = None,
    slack_store: SlackStore = Depends(_resolve_slack_store),
) -> Response:
    """Handle Slack OAuth callback.

    Args:
        code: OAuth authorization code
        state: OAuth state for verification
        error: OAuth error (if any)
        slack_store: Slack store

    Returns:
        Redirect to app or error page

    """
    if error:
        logger.error(f"Slack OAuth error: {error}")
        return Response(content=f"Slack OAuth error: {error}", status_code=400)

    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth code")

    # Verify state
    oauth_state = slack_store.get_oauth_state(state)
    if not oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    if not SLACK_SDK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Slack SDK not installed. Install with: pip install slack-sdk",
        )

    try:
        from slack_sdk import WebClient  # type: ignore[import-not-found]

        client = WebClient()

        # Exchange code for token
        response = client.oauth_v2_access(
            client_id=FORGE_config.SLACK_CLIENT_ID,
            client_secret=(FORGE_config.SLACK_CLIENT_SECRET.get_secret_value() if FORGE_config.SLACK_CLIENT_SECRET else None),
            code=code,
        )

        if not response.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange OAuth code",
            )

        # Save workspace
        workspace = SlackWorkspace(
            id=response["team"]["id"],
            team_id=response["team"]["id"],
            team_name=response["team"]["name"],
            bot_token=response["access_token"],
            bot_user_id=response["bot_user_id"],
            installed_by_user_id=oauth_state.user_id,
        )
        slack_store.save_workspace(workspace)

        # Save user link if user token is provided
        if "authed_user" in response and "id" in response["authed_user"]:
            user_link = SlackUserLink(
                slack_user_id=response["authed_user"]["id"],
                slack_workspace_id=workspace.team_id,
                FORGE_user_id=oauth_state.user_id,
                user_token=response["authed_user"].get("access_token"),
            )
            slack_store.save_user_link(user_link)

        # Clean up OAuth state
        slack_store.delete_oauth_state(state)

        # Redirect to success page
        redirect_url = oauth_state.redirect_url or "/settings/integrations"
        return Response(
            content=f'<html><body>Slack installed successfully! <a href="{redirect_url}">Return to Forge</a></body></html>',
            media_type="text/html",
        )

    except Exception as e:
        logger.error(f"Failed to complete Slack OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@app.post("/events")
async def slack_events(
    request: Request,
    slack_store: Annotated[SlackStore, Depends(get_slack_store)],
) -> JSONResponse:
    """Handle Slack event webhooks.

    Args:
        request: FastAPI request
        slack_store: Slack store

    Returns:
        JSON response

    """
    # Parse request body
    body = await request.json()

    # Handle URL verification challenge
    if body.get("type") == "url_verification":
        return JSONResponse({"challenge": body.get("challenge")})

    # Verify signature
    signing_secret = FORGE_config.SLACK_SIGNING_SECRET.get_secret_value() if FORGE_config.SLACK_SIGNING_SECRET else None
    if not await verify_slack_signature(request, signing_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # Handle event
    event = body.get("event", {})
    event_type = event.get("type")

    if event_type == "app_mention":
        await handle_app_mention(event, slack_store)
    elif event_type == "message":
        # Only handle thread replies
        if "thread_ts" in event and event.get("thread_ts") != event.get("ts"):
            await handle_thread_message(event, slack_store)

    return JSONResponse({"ok": True})


async def handle_app_mention(event: dict[str, Any], slack_store: SlackStore) -> None:
    """Handle @Forge mentions in Slack.

    Args:
        event: Slack event data
        slack_store: Slack store

    """
    team_id = event.get("team")
    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text", "")
    ts = event.get("ts")
    thread_ts = event.get("thread_ts", ts)  # Use ts if not in a thread

    logger.info(f"Handling app mention from user {user_id} in channel {channel_id}")

    if not all([team_id, channel_id, user_id, thread_ts]):
        logger.error("Slack event missing required identifiers: team_id=%s channel_id=%s user_id=%s thread_ts=%s", team_id, channel_id, user_id, thread_ts)
        return

    team_id = cast(str, team_id)
    channel_id = cast(str, channel_id)
    user_id = cast(str, user_id)
    thread_ts = cast(str, thread_ts)

    try:
        # Get workspace
        workspace = slack_store.get_workspace(team_id)
        if not workspace:
            logger.error(f"Workspace {team_id} not found")
            return

        # Get user link
        user_link = slack_store.get_user_link(team_id, user_id)
        if not user_link:
            # Send ephemeral message asking user to link their account
            client = SlackClient(workspace.bot_token)
            client.post_ephemeral_message(
                channel=channel_id,
                user=user_id,
                text="Please link your Forge account first at https://app.all-hands.dev/settings/integrations",
                thread_ts=thread_ts,
            )
            return

        # Check if this is a new conversation or continuation
        conv_link = slack_store.get_conversation_link(team_id, channel_id, thread_ts)

        if conv_link:
            # Continue existing conversation
            await continue_conversation(conv_link, text, workspace, slack_store)
        else:
            # Start new conversation
            await start_new_conversation(
                team_id,
                channel_id,
                thread_ts,
                user_id,
                text,
                user_link,
                workspace,
                slack_store,
            )

    except Exception as e:
        logger.error(f"Failed to handle app mention: {e}")


async def start_new_conversation(
    team_id: str,
    channel_id: str,
    thread_ts: str,
    user_id: str,
    text: str,
    user_link: SlackUserLink,
    workspace: SlackWorkspace,
    slack_store: SlackStore,
) -> None:
    """Start a new Forge conversation from Slack.

    Args:
        team_id: Slack team ID
        channel_id: Slack channel ID
        thread_ts: Slack thread timestamp
        user_id: Slack user ID
        text: Message text
        user_link: User link
        workspace: Workspace configuration
        slack_store: Slack store

    """
    client = SlackClient(workspace.bot_token)

    # Remove bot mention from text
    clean_text = client.remove_bot_mention(text, workspace.bot_user_id)

    # Extract repository if mentioned
    repository = client.extract_repo_from_text(clean_text)

    # Send loading message
    response = client.post_message(
        SlackOutgoingMessage(
            channel=channel_id,
            text=":hourglass_flowing_sand: Starting conversation...",
            thread_ts=thread_ts,
            blocks=None,
        ),
    )
    loading_ts = response["ts"]

    try:
        # Create Forge conversation
        init_request = InitSessionRequest(
            initial_user_msg=clean_text,
            repository=repository,
            conversation_id=uuid.uuid4().hex,
        )

        conversation_response = await new_conversation(
            data=init_request,
            user_id=user_link.FORGE_user_id,
            provider_tokens=_EMPTY_PROVIDER_TOKENS,
            user_secrets=None,
            auth_type=None,
        )

        if isinstance(conversation_response, JSONResponse):
            error_body = conversation_response.body
            if isinstance(error_body, (bytes, bytearray)):
                error_text = error_body.decode("utf-8", errors="replace")
            else:
                error_text = str(error_body)
            client.update_message(
                channel=channel_id,
                ts=loading_ts,
                text=f":x: Error starting conversation: {error_text}",
            )
            logger.error("Failed to start conversation via Slack (response %s)", error_text)
            return

        # Save conversation link
        conv_link = SlackConversationLink(
            slack_channel_id=channel_id,
            slack_thread_ts=thread_ts,
            slack_workspace_id=team_id,
            conversation_id=conversation_response.conversation_id,
            repository=repository,
            created_by_slack_user_id=user_id,
        )
        slack_store.save_conversation_link(conv_link)

        # Subscribe to agent events to stream updates to Slack
        from forge.events.stream import EventStreamSubscriber
        from forge.server.shared import conversation_manager

        agent_session = conversation_manager.get_agent_session(conversation_response.conversation_id)
        if agent_session:
            # Create event callback for streaming to Slack
            event_callback = create_slack_event_callback(
                client,
                channel_id,
                thread_ts,
                conversation_response.conversation_id,
            )

            try:
                # Subscribe to agent events
                agent_session.event_stream.subscribe(
                    EventStreamSubscriber.SERVER,
                    event_callback,
                    f"slack_{conversation_response.conversation_id}",
                )

                # Track the listener for cleanup
                _slack_event_listeners[conversation_response.conversation_id] = (client, channel_id, thread_ts)

                logger.info(f"Subscribed to events for Slack conversation {conversation_response.conversation_id}")
            except ValueError as e:
                # Subscription ID already exists, that's OK
                logger.debug(f"Event subscription already exists: {e}")

        # Update loading message with success
        client.update_message(
            channel=channel_id,
            ts=loading_ts,
            text=f":white_check_mark: Conversation started! I'll update you here as I work.\n\n*Or view live at:* https://app.all-hands.dev/conversations/{
                conversation_response.conversation_id}",
        )

        logger.info(
            f"Started conversation {conversation_response.conversation_id} from Slack",
        )

    except Exception as e:
        # Update loading message with error
        client.update_message(
            channel=channel_id,
            ts=loading_ts,
            text=f":x: Error: {e!s}",
        )
        logger.error(f"Failed to start conversation: {e}")
        raise


async def continue_conversation(
    conv_link: SlackConversationLink,
    text: str,
    workspace: SlackWorkspace,
    slack_store: SlackStore,
) -> None:
    """Continue an existing Forge conversation from Slack.

    Args:
        conv_link: Conversation link
        text: Message text
        workspace: Workspace configuration
        slack_store: Slack store

    """
    from forge.events.action import MessageAction
    from forge.server.shared import conversation_manager

    client = SlackClient(workspace.bot_token)

    # Remove bot mention from text
    clean_text = client.remove_bot_mention(text, workspace.bot_user_id)

    # Send loading message
    response = client.post_message(
        SlackOutgoingMessage(
            channel=conv_link.slack_channel_id,
            text=":hourglass_flowing_sand: Processing your message...",
            thread_ts=conv_link.slack_thread_ts,
            blocks=None,
        ),
    )
    loading_ts = response["ts"]

    try:
        # Send message to existing conversation
        event_dict = {
            "action": "message",
            "args": {"content": clean_text},
            "message": clean_text,
        }

        await conversation_manager.send_event_to_conversation(
            conv_link.conversation_id,
            event_dict,
        )

        # Update loading message with success
        client.update_message(
            channel=conv_link.slack_channel_id,
            ts=loading_ts,
            text=f":white_check_mark: Message sent to conversation!\n\n*View progress at:* https://app.all-hands.dev/conversations/{
                conv_link.conversation_id}",
        )

        logger.info(f"Continued conversation {conv_link.conversation_id} from Slack")

    except Exception as e:
        client.update_message(
            channel=conv_link.slack_channel_id,
            ts=loading_ts,
            text=f":x: Error: {e!s}",
        )
        logger.error(f"Failed to continue conversation: {e}")
        raise


async def handle_thread_message(event: dict[str, Any], slack_store: SlackStore) -> None:
    """Handle thread replies (without @mention).

    Args:
        event: Slack event data
        slack_store: Slack store

    """
    team_id = event.get("team")
    channel_id = event.get("channel")
    event.get("user")
    text = event.get("text", "")
    thread_ts = event.get("thread_ts")

    # Ignore bot's own messages
    if event.get("bot_id"):
        return

    logger.debug(f"Thread message received: {text}")

    if not all([team_id, channel_id, thread_ts]):
        logger.debug("Skipping thread message due to missing identifiers")
        return

    team_id = cast(str, team_id)
    channel_id = cast(str, channel_id)
    thread_ts = cast(str, thread_ts)

    # Get conversation link for this thread
    conv_link = slack_store.get_conversation_link(team_id, channel_id, thread_ts)
    if not conv_link:
        # Not an Forge conversation thread
        return

    # Get workspace
    workspace = slack_store.get_workspace(team_id)
    if not workspace:
        return

    # Continue the conversation (same as @mention, but without requiring the mention)
    await continue_conversation(conv_link, text, workspace, slack_store)


@app.get("/workspaces")
async def list_workspaces(
    user_id: str,
    slack_store: Annotated[SlackStore, Depends(_resolve_slack_store)],
) -> JSONResponse:
    """List all Slack workspaces installed by user.

    Args:
        user_id: Forge user ID
        slack_store: Slack store

    Returns:
        List of workspaces

    """
    workspaces = slack_store.list_workspaces()
    user_workspaces = [ws for ws in workspaces if ws.installed_by_user_id == user_id]

    return JSONResponse(
        {
            "workspaces": [{"team_id": ws.team_id, "team_name": ws.team_name} for ws in user_workspaces],
        },
    )


@app.delete("/workspaces/{team_id}")
async def uninstall_workspace(
    team_id: str,
    user_id: str,
    slack_store: Annotated[SlackStore, Depends(_resolve_slack_store)],
) -> JSONResponse:
    """Uninstall a Slack workspace.

    Args:
        team_id: Slack team ID
        user_id: Forge user ID (for verification)
        slack_store: Slack store

    Returns:
        Success response

    """
    workspace = slack_store.get_workspace(team_id)
    if not workspace or workspace.installed_by_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    slack_store.delete_workspace(team_id)
    return JSONResponse({"ok": True})


@app.post("/cleanup/{conversation_id}")
async def cleanup_slack_listener(
    conversation_id: str,
) -> JSONResponse:
    """Clean up Slack event listener for a finished conversation.

    Args:
        conversation_id: Forge conversation ID

    Returns:
        Success response

    """
    if conversation_id in _slack_event_listeners:
        del _slack_event_listeners[conversation_id]
        logger.info(f"Cleaned up Slack listener for conversation {conversation_id}")

    return JSONResponse({"ok": True})


# Expose router for inclusion and FastAPI app for direct testing
router = app
_slack_test_app = FastAPI()
_slack_test_app.include_router(router)
