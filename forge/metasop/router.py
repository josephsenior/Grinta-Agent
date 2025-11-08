"""Server-side routing helpers to invoke MetaSOP orchestrations and stream events."""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

from forge.core.logger import forge_logger as logger
from forge.server.shared import config, conversation_manager


def _get_orchestrator_class():
    """Get the MetaSOP orchestrator class.

    Dynamically imports and returns the MetaSOPOrchestrator class, used for
    managing multi-step orchestrated workflows in MetaSOP operations.

    Returns:
        type: MetaSOPOrchestrator class for instantiation

    Raises:
        ImportError: If orchestrator module cannot be imported

    Example:
        >>> OrchestratorClass = _get_orchestrator_class()
        >>> orchestrator = OrchestratorClass("default_sop", config)

    """
    from .orchestrator import MetaSOPOrchestrator

    return MetaSOPOrchestrator


def _create_orchestrator():
    """Create a new MetaSOP orchestrator instance.

    Instantiates a MetaSOPOrchestrator with the configured default SOP (System
    of Procedure). Loads configuration from the extended config settings.

    Returns:
        MetaSOPOrchestrator: Configured orchestrator instance ready for use

    Raises:
        ConfigurationError: If default_sop is not found in config

    Example:
        >>> orchestrator = _create_orchestrator()
        >>> await orchestrator.execute_sop(conversation_id, message)

    """
    from .orchestrator import MetaSOPOrchestrator

    # Get the default SOP from config
    metasop_cfg = getattr(config.extended, "metasop", {})
    default_sop = metasop_cfg.get("default_sop", "feature_delivery_with_ui")

    return MetaSOPOrchestrator(default_sop, config)


async def _setup_step_event_processing(
    conversation_id: str,
    orchestrator,
) -> asyncio.Task:
    """Set up step event processing for real-time orchestration updates.

    Creates an async queue and callback system to emit step events to the client
    in real-time as the orchestrator progresses through workflow steps. Handles
    both successful steps and retry attempts.

    Args:
        conversation_id: The conversation ID for routing events to correct client
        orchestrator: The orchestrator instance to register callbacks on

    Returns:
        asyncio.Task: Background task processing step events from the queue

    Raises:
        Exception: Any exceptions during event processing are logged but don't stop processing

    Example:
        >>> task = await _setup_step_event_processing(conv_id, orchestrator)
        >>> # Task runs in background, emitting step events to client
        >>> await task  # Runs until orchestration complete

    """
    step_event_queue: asyncio.Queue[tuple[str, str, str, int]] = asyncio.Queue()

    def emit_step_callback(step_id: str, role: str, status: str, retries: int = 0) -> None:
        """Callback to queue step events."""
        try:
            step_event_queue.put_nowait((step_id, role, status, retries))
        except Exception as e:
            logger.warning("Failed to queue step event: %s", e)

    orchestrator.set_step_event_callback(emit_step_callback)

    async def process_step_events() -> None:
        """Process step events from the queue."""
        while True:
            try:
                step_id, role, status, retries = await step_event_queue.get()
                await _emit_step_event_realtime(
                    conversation_id,
                    step_id,
                    role,
                    status,
                    retries,
                )
                step_event_queue.task_done()
            except Exception as e:
                logger.warning("Failed to process step event: %s", e)
                break

    return asyncio.create_task(process_step_events())


async def _validate_and_prepare_orchestration(
    conversation_id: str,
    raw_message: str,
) -> str | None:
    """Validate MetaSOP configuration and prepare the message.

    Args:
        conversation_id: The conversation ID.
        raw_message: The raw message to process.

    Returns:
        str | None: The cleaned message if valid, None if validation failed.

    """
    if not _is_metasop_enabled():
        logger.warning("MetaSOP is disabled in config")
        await _emit_status(conversation_id, "error", "MetaSOP is disabled in config")
        return None

    logger.info("MetaSOP is enabled, proceeding with orchestration")

    # Clean and process message
    cleaned_message = _clean_message(raw_message)
    logger.info("Cleaned message: %s", cleaned_message[:100])

    await _emit_status(conversation_id, "info", "MetaSOP orchestration started")

    return cleaned_message


async def _run_orchestration_with_events(
    conversation_id: str,
    cleaned_message: str,
    repo_root: str | None,
    llm_registry,
) -> tuple[bool, dict]:
    """Run the orchestration with event processing.

    Args:
        conversation_id: The conversation ID.
        cleaned_message: The cleaned message to process.
        repo_root: The repository root path.
        llm_registry: The LLM registry to use.

    Returns:
        tuple[bool, dict]: Success status and artifacts.

    """
    # Get the session's LLM registry if not provided
    if not llm_registry:
        llm_registry = _get_session_llm_registry(conversation_id)

    # Create and configure orchestrator
    orchestrator = _create_and_configure_orchestrator()
    if llm_registry:
        orchestrator.llm_registry = llm_registry

    # Set up event processing
    event_processor_task = await _setup_step_event_processing(
        conversation_id,
        orchestrator,
    )

    try:
        logger.info("Starting orchestrator.run_async with message: %s", cleaned_message[:100])
        ok, artifacts = await orchestrator.run_async(
            cleaned_message,
            repo_root,
            2,
        )

        # Cancel the event processor task
        event_processor_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await event_processor_task

        return ok, artifacts

    except Exception:
        # Ensure event processor is cancelled
        event_processor_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await event_processor_task
        raise


async def run_metasop_for_conversation(
    conversation_id: str,
    user_id: str | None,
    raw_message: str,
    repo_root: str | None = None,
    llm_registry=None,
) -> None:
    """Execute MetaSOP orchestration flow for a conversation and emit updates.

    This runs in the background and sends compact status updates to the
    conversation room so the UI can reflect progress.

    Args:
        conversation_id: The ID of the conversation.
        user_id: The ID of the user (optional).
        raw_message: The raw message to process.
        repo_root: The repository root path (optional).
        llm_registry: The LLM registry to use (optional).

    """
    logger.info(
        "run_metasop_for_conversation called: conversation_id=%s, user_id=%s, raw_message=%s",
        conversation_id,
        user_id,
        raw_message[:100],
    )

    try:
        # Validate and prepare
        cleaned_message = await _validate_and_prepare_orchestration(
            conversation_id,
            raw_message,
        )
        if not cleaned_message:
            return

        # Run orchestration with event processing
        ok, artifacts = await _run_orchestration_with_events(
            conversation_id,
            cleaned_message,
            repo_root,
            llm_registry,
        )

        # Create orchestrator for result processing (we need it for the results)
        orchestrator = _create_and_configure_orchestrator()

        # Process results
        await _process_orchestration_results(
            conversation_id,
            orchestrator,
            ok,
            artifacts,
        )

    except Exception as e:
        logger.exception("MetaSOP orchestration failed: %s", e)
        await _handle_orchestration_error(conversation_id, e)


def _is_metasop_enabled() -> bool:
    """Check if MetaSOP is enabled in configuration."""
    metasop_cfg: dict | None = getattr(config.extended, "metasop", None)
    return bool(metasop_cfg and metasop_cfg.get("enabled", False))


def _clean_message(raw_message: str) -> str:
    """Clean the raw message by removing SOP prefix if present.

    Strips the "sop:" prefix from the beginning of messages, which users may
    include to explicitly trigger MetaSOP mode. Normalizes the message for
    processing regardless of whether prefix was included.

    Args:
        raw_message: The raw input message potentially containing "sop:" prefix

    Returns:
        str: Cleaned message with prefix removed and whitespace trimmed

    Example:
        >>> _clean_message("sop: implement user authentication")
        "implement user authentication"
        >>> _clean_message("SOP: fix the bug")
        "fix the bug"
        >>> _clean_message("regular message")
        "regular message"

    """
    cleaned = raw_message
    if cleaned.lower().startswith("sop:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    return cleaned


def _get_session_llm_registry(conversation_id: str):
    """Get the LLM registry from the session for the given conversation ID.

    Args:
        conversation_id: The ID of the conversation to get the LLM registry for.

    Returns:
        LLM registry from the session, or None if not found.

    """
    try:
        # Get the session from the conversation manager
        if hasattr(conversation_manager, "_local_agent_loops_by_sid"):
            session = conversation_manager._local_agent_loops_by_sid.get(
                conversation_id,
            )
            if session and hasattr(session, "llm_registry"):
                logger.info("Found LLM registry for conversation %s", conversation_id)
                return session.llm_registry
            logger.warning(
                "No session or LLM registry found for conversation %s",
                conversation_id,
            )
        else:
            logger.warning(
                "Conversation manager does not have _local_agent_loops_by_sid",
            )
    except Exception as e:
        logger.warning(
            "Failed to get LLM registry for conversation %s: %s",
            conversation_id,
            e,
        )

    return None


def _create_and_configure_orchestrator():
    """Create and configure the MetaSOP orchestrator with enhanced settings.

    Returns:
        MetaSOPOrchestrator: A configured orchestrator instance.

    """
    metasop_cfg = getattr(config.extended, "metasop", {})
    OrchestratorCls = _get_orchestrator_class()
    return OrchestratorCls(
        sop_name=metasop_cfg.get("default_sop", "feature_delivery"),
        config=config,
    )


async def _process_orchestration_results(
    conversation_id: str,
    orchestrator,
    ok: bool,
    artifacts: dict,
) -> None:
    """Process orchestration results and emit status updates."""
    # Emit step events
    await _emit_step_events(conversation_id, orchestrator)

    # Emit artifacts for diagram generation
    await _emit_artifacts(conversation_id, artifacts)

    # Generate summary
    summary = _generate_summary(orchestrator, artifacts)

    # Persist results
    await _persist_orchestration_results(orchestrator, ok, artifacts, summary)

    # Emit final status
    await _emit_final_status(conversation_id, ok, summary)


async def _emit_step_events(conversation_id: str, orchestrator) -> None:
    """Emit status updates for each orchestration step."""
    try:
        report = orchestrator.get_verification_report()
        for evt in report.get("events", []):
            status_type = "info" if evt.get("status") in {"executed", "executed_shaped"} else "debug"
            message = f"step:{
                evt.get('step_id')} role:{
                evt.get('role')} status:{
                evt.get('status')} retries:{
                evt.get(
                    'retries',
                    0)}"
            await _emit_status(conversation_id, status_type, message)
    except Exception:
        pass


async def _emit_artifacts(conversation_id: str, artifacts: dict) -> None:
    """Emit artifacts to frontend for diagram generation.

    Args:
        conversation_id: The conversation ID
        artifacts: The artifacts dictionary from orchestration

    """
    try:
        for step_id, artifact in artifacts.items():
            # Extract artifact content
            artifact_content = None
            if hasattr(artifact, "content"):
                artifact_content = artifact.content
            elif isinstance(artifact, dict):
                artifact_content = artifact

            # Skip artifacts without parseable content
            if not artifact_content:
                continue

            # Parse __raw__ JSON if present
            raw_json = None
            if isinstance(artifact_content, dict) and "__raw__" in artifact_content:
                try:
                    raw_json = json.loads(artifact_content["__raw__"])
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to parse __raw__ JSON for {step_id}")

            # Emit artifact data as a status message with embedded JSON
            artifact_data = raw_json if raw_json else artifact_content

            # Send as a formatted message that the frontend can parse
            message = f"Artifact produced for step: {step_id}\n```json\n{json.dumps(artifact_data, indent=2)}\n```"
            await _emit_status(conversation_id, "info", message)
            logger.info(f"Emitted artifact for step {step_id}")

    except Exception as e:
        logger.warning(f"Failed to emit artifacts: {e}")


async def _emit_step_event_realtime(
    conversation_id: str,
    step_id: str,
    role: str,
    status: str,
    retries: int = 0,
) -> None:
    """Emit a single step event in real-time to the frontend."""
    try:
        status_type = "info" if status in {"executed", "executed_shaped", "success"} else "debug"
        message = f"step:{step_id} role:{role} status:{status} retries:{retries}"
        await _emit_status(conversation_id, status_type, message)
        logger.debug("Emitted real-time step event: %s", message)
    except Exception as e:
        logger.warning("Failed to emit real-time step event: %s", e)


def _generate_summary(orchestrator, artifacts: dict) -> str:
    """Generate summary of orchestration results."""
    summary = _summarize_artifacts(artifacts)

    try:
        executed = orchestrator.get_verification_report().get("executed_steps", [])
        summary = f"{summary} executed={executed}"
    except Exception:
        pass

    return summary


async def _persist_orchestration_results(
    orchestrator,
    ok: bool,
    artifacts: dict,
    summary: str,
) -> None:
    """Persist orchestration results to log files."""
    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Get report and prepare serializable artifacts
        report = orchestrator.get_verification_report()
        serializable_artifacts = _prepare_serializable_artifacts(artifacts)

        # Write detailed report
        _write_detailed_report(logs_dir, ok, summary, report, serializable_artifacts)

        # Write summary log
        _write_summary_log(logs_dir, ok, report)

    except Exception:
        # Note: conversation_id not available in this context
        pass


def _prepare_serializable_artifacts(artifacts: dict) -> dict:
    """Prepare artifacts for serialization."""
    serializable_artifacts = {}
    for k, art in artifacts.items():
        try:
            serializable_artifacts[k] = art.content
        except Exception:
            serializable_artifacts[k] = {"_error": "unserializable"}
    return serializable_artifacts


def _write_detailed_report(
    logs_dir: Path,
    ok: bool,
    summary: str,
    report: dict,
    serializable_artifacts: dict,
) -> None:
    """Write detailed report to JSON file."""
    payload = {
        "ok": ok,
        "summary": summary,
        "report": report,
        "artifacts": serializable_artifacts,
    }
    (logs_dir / "metasop_last_run.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _write_summary_log(logs_dir: Path, ok: bool, report: dict) -> None:
    """Write summary log to NDJSON file."""
    total_tokens, total_duration, retries_sum = _calculate_metrics(report)

    nd_line = {
        "ts": int(asyncio.get_event_loop().time() * 1000),
        "ok": ok,
        "steps": report.get("all_steps", []),
        "executed": report.get("executed_steps", []),
        "tokens": total_tokens,
        "duration_ms": total_duration,
        "retries": retries_sum,
    }

    with (logs_dir / "metasop_runs.ndjson").open("a", encoding="utf-8") as f:
        f.write(json.dumps(nd_line) + "\n")


def _calculate_metrics(report: dict) -> tuple[int, int, int]:
    """Calculate total tokens, duration, and retries from orchestration report.

    Aggregates performance metrics from all executed steps in the orchestration
    report to provide overall statistics on resource usage and resilience.

    Args:
        report: Dictionary containing orchestration report with events and metrics

    Returns:
        tuple[int, int, int]: Tuple of (total_tokens, total_duration_ms, total_retries)
            - total_tokens: Sum of tokens used across all executed steps
            - total_duration_ms: Total duration in milliseconds
            - total_retries: Total number of retries across all steps

    Example:
        >>> report = {
        ...     "events": [
        ...         {"status": "executed", "total_tokens": 100, "duration_ms": 500, "retries": 1},
        ...         {"status": "executed", "total_tokens": 50, "duration_ms": 300, "retries": 0},
        ...     ]
        ... }
        >>> tokens, duration, retries = _calculate_metrics(report)
        >>> tokens, duration, retries
        (150, 800, 1)

    """
    total_tokens = 0
    total_duration = 0
    retries_sum = 0

    for evt in report.get("events", []):
        if evt.get("status") in {"executed", "executed_shaped"}:
            total_tokens += evt.get("total_tokens") or 0
            total_duration += evt.get("duration_ms") or 0
            retries_sum += evt.get("retries") or 0

    return total_tokens, total_duration, retries_sum


async def _emit_final_status(conversation_id: str, ok: bool, summary: str) -> None:
    """Emit final status based on orchestration success."""
    if ok:
        await _emit_status(
            conversation_id,
            "info",
            f"MetaSOP finished successfully. Summary: {summary}",
        )
    else:
        await _emit_status(
            conversation_id,
            "error",
            f"MetaSOP failed before completion. Partial summary: {summary}",
        )


async def _handle_orchestration_error(conversation_id: str, e: Exception) -> None:
    """Handle orchestration errors."""
    logger.exception("MetaSOP orchestration crashed: %s", e)
    error_msg = f"MetaSOP error: {e.__class__.__name__}: {str(e)[:200]}"
    logger.error("Full error message being sent to frontend: %s", error_msg)
    with contextlib.suppress(Exception):
        await _emit_status(
            conversation_id,
            "error",
            error_msg,
        )


async def _emit_status(conversation_id: str, msg_type: str, message: str) -> None:
    """Emit a lightweight status update to the conversation room."""
    try:
        import time

        payload = {
            "status_update": True,
            "type": msg_type,
            "message": message,
            "id": f"metasop_{int(time.time() * 1000)}",
        }
        logger.info(
            "Emitting MetaSOP status: conversation_id=%s, type=%s, message=%s",
            conversation_id,
            msg_type,
            message,
        )
        await conversation_manager.sio.emit(
            "oh_event",
            payload,
            to=f"room:{conversation_id}",
        )
        logger.info("MetaSOP status emitted successfully")
    except Exception as e:
        logger.warning("Failed to emit MetaSOP status for %s: %s", conversation_id, e)


def _summarize_artifacts(artifacts: dict) -> str:
    try:
        keys = list(artifacts.keys())
        qa = artifacts.get("qa_verify") or artifacts.get("qa")
        qa_str = ""
        if qa and isinstance(qa.content, dict):
            ok = qa.content.get("ok")
            tests = qa.content.get("tests", {})
            qa_str = f" | QA ok={ok} tests={tests}"
        return f"steps={keys}{qa_str}"
    except Exception:
        try:
            return json.dumps(dict.fromkeys(artifacts, "ok"))
        except Exception:
            return "unavailable"
