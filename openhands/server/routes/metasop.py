"""MetaSOP API routes for retrieving orchestration data."""

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openhands.core.logger import openhands_logger as logger

app = APIRouter(prefix="/api/metasop")


@app.get("/orchestration/{conversation_id}")
async def get_orchestration_data(conversation_id: str) -> JSONResponse:
    """Get orchestration artifacts and diagram data for a conversation.

    Args:
        conversation_id: The conversation ID

    Returns:
        JSONResponse with orchestration data including artifacts and diagram
    """
    try:
        # For now, return the last run data from logs
        # TODO: Store per-conversation orchestration data
        logs_dir = Path("logs")
        last_run_file = logs_dir / "metasop_last_run.json"

        if not last_run_file.exists():
            return JSONResponse(
                {
                    "status": "not_found",
                    "message": "No orchestration data found",
                    "artifacts": {},
                    "diagram": None,
                },
            )

        # Read the last run data
        data = json.loads(last_run_file.read_text(encoding="utf-8"))

        # Generate Mermaid diagram from the report
        diagram = _generate_mermaid_diagram(
            data.get("report", {}),
            data.get("artifacts", {}),
        )

        # Extract key information
        response_data = {
            "status": "success" if data.get("ok") else "failed",
            "summary": data.get("summary", ""),
            "artifacts": data.get("artifacts", {}),
            "diagram": diagram,
            "report": data.get("report", {}),
        }

        return JSONResponse(response_data)

    except Exception as e:
        logger.error(f"Failed to get orchestration data: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


def _generate_mermaid_diagram(report: dict, artifacts: dict) -> str:
    """Generate a Mermaid diagram from the orchestration report.

    Args:
        report: The orchestration report
        artifacts: The artifacts from the orchestration

    Returns:
        str: Mermaid diagram markup
    """
    try:
        events = report.get("events", [])
        if not events:
            return _generate_default_diagram()

        # Build the diagram
        lines = ["graph TD"]

        # Track nodes and their status
        nodes = {}
        for i, evt in enumerate(events):
            step_id = evt.get("step_id", f"step_{i}")
            role = evt.get("role", "Unknown")
            status = evt.get("status", "unknown")
            retries = evt.get("retries", 0)

            # Create node label
            if retries > 0:
                label = f"{role}<br/>{step_id}<br/>(retries: {retries})"
            else:
                label = f"{role}<br/>{step_id}"

            # Determine node style based on status
            style_class = _get_node_style_class(status)

            node_id = f"node{i}"
            nodes[step_id] = {
                "id": node_id,
                "label": label,
                "style": style_class,
                "index": i,
            }

            # Add node
            lines.append(f'    {node_id}["{label}"]:::{style_class}')

        # Add connections based on dependencies
        for i, evt in enumerate(events):
            if i > 0:
                # Connect to previous step
                prev_node = f"node{i - 1}"
                curr_node = f"node{i}"
                lines.append(f"    {prev_node} --> {curr_node}")

        # Add style classes
        lines.extend(
            [
                "",
                "    classDef executed fill:#4ade80,stroke:#22c55e,stroke-width:2px,color:#000",
                "    classDef failed fill:#f87171,stroke:#ef4444,stroke-width:2px,color:#000",
                "    classDef skipped fill:#94a3b8,stroke:#64748b,stroke-width:2px,color:#000",
                "    classDef pending fill:#fbbf24,stroke:#f59e0b,stroke-width:2px,color:#000",
            ],
        )

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Failed to generate Mermaid diagram: {e}")
        return _generate_default_diagram()


def _get_node_style_class(status: str) -> str:
    """Get the CSS class for a node based on its status.

    Args:
        status: The step status

    Returns:
        str: CSS class name
    """
    status_map = {
        "executed": "executed",
        "executed_shaped": "executed",
        "success": "executed",
        "failed": "failed",
        "skipped": "skipped",
        "pending": "pending",
    }
    return status_map.get(status, "pending")


def _generate_default_diagram() -> str:
    """Generate a default diagram when no data is available.

    Returns:
        str: Default Mermaid diagram
    """
    return """graph TD
    Start[MetaSOP]:::pending
    Start --> PM[Product Manager<br/>Specification]:::pending
    PM --> Arch[Architect<br/>Design]:::pending
    Arch --> Eng[Engineer<br/>Implementation]:::pending
    Eng --> QA[QA<br/>Verification]:::pending
    QA --> Done[Complete]:::pending

    classDef executed fill:#4ade80,stroke:#22c55e,stroke-width:2px,color:#000
    classDef failed fill:#f87171,stroke:#ef4444,stroke-width:2px,color:#000
    classDef skipped fill:#94a3b8,stroke:#64748b,stroke-width:2px,color:#000
    classDef pending fill:#fbbf24,stroke:#f59e0b,stroke-width:2px,color:#000
"""


@app.get("/artifacts/{conversation_id}/{step_id}")
async def get_step_artifact(conversation_id: str, step_id: str) -> JSONResponse:
    """Get the artifact for a specific step.

    Args:
        conversation_id: The conversation ID
        step_id: The step ID

    Returns:
        JSONResponse with the step artifact
    """
    try:
        logs_dir = Path("logs")
        last_run_file = logs_dir / "metasop_last_run.json"

        if not last_run_file.exists():
            raise HTTPException(status_code=404, detail="No orchestration data found")

        data = json.loads(last_run_file.read_text(encoding="utf-8"))
        artifacts = data.get("artifacts", {})

        if step_id not in artifacts:
            raise HTTPException(
                status_code=404,
                detail=f"Artifact not found for step: {step_id}",
            )

        return JSONResponse({"step_id": step_id, "artifact": artifacts[step_id]})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get step artifact: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


class PassToCodeActRequest(BaseModel):
    """Request to pass MetaSOP artifacts to CodeAct for execution."""

    conversation_id: str
    user_request: str
    repo_root: Optional[str] = None


@app.post("/pass-to-codeact")
async def pass_to_codeact(request: PassToCodeActRequest) -> JSONResponse:
    """Pass MetaSOP artifacts to CodeAct agent for execution.

    This endpoint:
    1. Loads MetaSOP artifacts from the last run
    2. Formats them into a comprehensive implementation prompt
    3. Returns the formatted prompt for the frontend to send to CodeAct

    Args:
        request: Request containing conversation_id and user_request

    Returns:
        JSONResponse with the formatted CodeAct prompt
    """
    try:
        # Load MetaSOP artifacts
        logs_dir = Path("logs")
        last_run_file = logs_dir / "metasop_last_run.json"

        if not last_run_file.exists():
            raise HTTPException(
                status_code=404,
                detail="No MetaSOP orchestration data found. Please run MetaSOP first.",
            )

        data = json.loads(last_run_file.read_text(encoding="utf-8"))
        artifacts = data.get("artifacts", {})

        if not artifacts:
            raise HTTPException(
                status_code=400,
                detail="No artifacts found in MetaSOP orchestration.",
            )

        # Format artifacts for CodeAct
        codeact_prompt = _format_artifacts_for_codeact(
            artifacts, request.user_request, request.repo_root
        )

        logger.info(
            f"Generated CodeAct prompt ({len(codeact_prompt)} chars) for conversation {request.conversation_id}"
        )

        return JSONResponse(
            {
                "success": True,
                "prompt": codeact_prompt,
                "artifacts_count": len(artifacts),
                "message": "MetaSOP artifacts formatted for CodeAct execution",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pass to CodeAct: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


def _format_artifacts_for_codeact(
    artifacts: dict, user_request: str, repo_root: Optional[str] = None
) -> str:
    """Format MetaSOP artifacts into a comprehensive CodeAct prompt.

    Args:
        artifacts: Dictionary of MetaSOP artifacts
        user_request: Original user request
        repo_root: Optional repository root path

    Returns:
        Formatted prompt for CodeAct
    """
    prompt_parts = [
        "# 🚀 Implementation Task (Generated from MetaSOP Planning)",
        "",
        f"## Original Request:",
        user_request,
        "",
        "---",
        "",
    ]

    # Add PM Specification
    pm_artifact = artifacts.get("pm_spec")
    if pm_artifact:
        pm_content = pm_artifact.get("content", {})
        prompt_parts.extend(
            [
                "## 📋 Product Manager Specifications:",
                "",
                f"**User Stories:**",
                str(pm_content.get("user_stories", "N/A")),
                "",
                f"**Acceptance Criteria:**",
                str(pm_content.get("acceptance_criteria", "N/A")),
                "",
                f"**Requirements:**",
                str(pm_content.get("requirements", "N/A")),
                "",
                "---",
                "",
            ]
        )

    # Add Architect Design
    arch_artifact = artifacts.get("arch_design")
    if arch_artifact:
        arch_content = arch_artifact.get("content", {})
        prompt_parts.extend(
            [
                "## 🏗️ Architect System Design:",
                "",
                f"**Architecture:**",
                str(arch_content.get("architecture", "N/A")),
                "",
                f"**API Specifications:**",
                str(arch_content.get("api_specs", "N/A")),
                "",
                f"**Database Schema:**",
                str(arch_content.get("database_schema", "N/A")),
                "",
            ]
        )

        tech_decisions = arch_content.get("technical_decisions", [])
        if tech_decisions:
            prompt_parts.extend(["**Technical Decisions:**", ""])
            for dec in tech_decisions:
                if isinstance(dec, dict):
                    decision = dec.get("decision", "")
                    rationale = dec.get("rationale", "")
                    prompt_parts.append(f"- **{decision}**: {rationale}")
            prompt_parts.extend(["", "---", ""])

    # Add Engineer Implementation Plan (THE MOST IMPORTANT!)
    eng_artifact = artifacts.get("engineer_impl")
    if eng_artifact:
        eng_content = eng_artifact.get("content", {})

        prompt_parts.extend(
            [
                "## 👨‍💻 Engineer Implementation Blueprint:",
                "",
            ]
        )

        # File Structure
        file_structure = eng_content.get("file_structure")
        if file_structure:
            prompt_parts.extend(
                [
                    "### 📁 File Structure:",
                    "```",
                    _format_file_tree(file_structure),
                    "```",
                    "",
                ]
            )

        # Implementation Plan
        impl_plan = eng_content.get(
            "implementation_plan", eng_content.get("implementation_summary", "")
        )
        if impl_plan:
            prompt_parts.extend(
                [
                    "### 📝 Implementation Steps:",
                    impl_plan,
                    "",
                ]
            )

        # Dependencies
        dependencies = eng_content.get("dependencies", [])
        if dependencies:
            prompt_parts.extend(["### 📦 Required Dependencies:", ""])
            for dep in dependencies:
                prompt_parts.append(f"- {dep}")
            prompt_parts.extend(["", ""])

        # Technical Decisions (from engineer)
        tech_decisions = eng_content.get("technical_decisions", [])
        if tech_decisions:
            prompt_parts.extend(["### 🔧 Technical Decisions:", ""])
            for dec in tech_decisions:
                if isinstance(dec, dict):
                    decision = dec.get("decision", "")
                    rationale = dec.get("rationale", "")
                    prompt_parts.append(f"- **{decision}**: {rationale}")
            prompt_parts.extend(["", ""])

        # Run Results (commands)
        run_results = eng_content.get("run_results", {})
        if run_results:
            prompt_parts.extend(["### ⚙️ Setup & Run Commands:", ""])
            
            setup_cmds = run_results.get("setup_commands", [])
            if setup_cmds:
                prompt_parts.append("**Setup:**")
                for cmd in setup_cmds:
                    prompt_parts.append(f"```bash\n{cmd}\n```")
                prompt_parts.append("")

            test_cmds = run_results.get("test_commands", [])
            if test_cmds:
                prompt_parts.append("**Testing:**")
                for cmd in test_cmds:
                    prompt_parts.append(f"```bash\n{cmd}\n```")
                prompt_parts.append("")

            dev_cmds = run_results.get("dev_commands", [])
            if dev_cmds:
                prompt_parts.append("**Development:**")
                for cmd in dev_cmds:
                    prompt_parts.append(f"```bash\n{cmd}\n```")
                prompt_parts.append("")

        prompt_parts.extend(["---", ""])

    # Add UI Design (if available)
    ui_artifact = artifacts.get("ui_design")
    if ui_artifact:
        ui_content = ui_artifact.get("content", {})
        prompt_parts.extend(
            [
                "## 🎨 UI Designer Layout Plan:",
                "",
                f"**Component Hierarchy:**",
                str(ui_content.get("component_hierarchy", "N/A")),
                "",
                f"**Design Tokens:**",
                str(ui_content.get("design_tokens", "N/A")),
                "",
                "---",
                "",
            ]
        )

    # Add final instructions
    prompt_parts.extend(
        [
            "## ✅ Your Task:",
            "",
            "You are CodeAct agent. Implement the feature as specified above:",
            "",
            "1. **Create all files** as specified in the file structure",
            "2. **Follow the architecture** and API specifications",
            "3. **Implement technical decisions** as documented",
            "4. **Install dependencies** as listed",
            "5. **Write comprehensive tests** with good coverage",
            "6. **Follow best practices** for code quality and security",
            "7. **Run the setup, test, and dev commands** to verify everything works",
            "",
            "Start implementation now. Create the files step by step, install dependencies, write code, and test.",
        ]
    )

    if repo_root:
        prompt_parts.extend(
            [
                "",
                f"**Working Directory:** `{repo_root}`",
            ]
        )

    return "\n".join(prompt_parts)


def _format_file_tree(file_structure: Any, indent: int = 0) -> str:
    """Format file structure as a tree.

    Args:
        file_structure: File structure object (dict or list)
        indent: Current indentation level

    Returns:
        Formatted file tree string
    """
    if not file_structure:
        return "  " * indent + "(No files specified)"

    # Handle wrapped structure
    if isinstance(file_structure, dict) and "root" in file_structure:
        file_structure = file_structure["root"]

    lines = []

    if isinstance(file_structure, dict):
        name = file_structure.get(
            "name",
            file_structure.get("file", file_structure.get("path", "Unknown")),
        )
        file_type = file_structure.get("type", "file")
        description = file_structure.get("description", "")

        prefix = "📁 " if file_type == "folder" else "📄 "
        lines.append(f"{'  ' * indent}{prefix}{name}")

        if description:
            lines.append(f"{'  ' * (indent + 1)}# {description}")

        # Handle children
        children = file_structure.get("children", [])
        for child in children:
            lines.append(_format_file_tree(child, indent + 1))

    elif isinstance(file_structure, list):
        for item in file_structure:
            lines.append(_format_file_tree(item, indent))

    return "\n".join(lines)
