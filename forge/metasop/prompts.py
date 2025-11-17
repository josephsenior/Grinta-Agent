"""Prompt and example builders used by MetaSOP for role-specific guidance."""

from __future__ import annotations

import contextlib
import json
from typing import Any


def build_minimal_example_from_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Create a tiny JSON object that satisfies 'required' keys in a simple way."""
    example: dict[str, Any] = {}
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = schema.get("required", []) if isinstance(schema, dict) else []
    for key in required:
        t = (props.get(key) or {}).get("type")
        if t == "string":
            example[key] = ""
        elif t == "boolean":
            example[key] = False
        elif t == "integer":
            example[key] = 0
        elif t == "array":
            example[key] = []
        elif t == "object":
            example[key] = {}
        else:
            example[key] = None
    return example


def build_pm_example() -> dict[str, Any]:
    """Create a realistic example for PM output with actual content."""
    return {
        "user_stories": [
            {
                "id": "US-001",
                "title": "User can register with email and password",
                "story": "As a new user, I want to create an account with my email and password, so that I can securely access the platform",
                "description": "Users need a secure way to create accounts. This includes email validation, password strength requirements, and account confirmation.",
                "priority": "high",
                "acceptance_criteria": [
                    "User can enter email and password on registration form",
                    "Password must be minimum 8 characters with mixed case and numbers",
                    "System validates email format before accepting",
                    "User receives confirmation email after registration",
                    "User can immediately login after registration",
                ],
                "dependencies": [],
                "estimated_complexity": "medium",
                "user_value": "Enables users to create secure personal accounts and access personalized features",
            },
            {
                "id": "US-002",
                "title": "User can view and edit their profile",
                "story": "As a registered user, I want to view and update my profile information, so that I can keep my details current",
                "description": "Users should be able to manage their personal information including name, email, avatar, and preferences.",
                "priority": "medium",
                "acceptance_criteria": [
                    "User can access profile page from main navigation",
                    "User can edit name, bio, and avatar image",
                    "Changes save immediately with visual confirmation",
                    "Email changes require re-verification",
                    "Profile displays correctly on mobile and desktop",
                ],
                "dependencies": ["US-001"],
                "estimated_complexity": "small",
                "user_value": "Users can personalize their account and maintain accurate information",
            },
        ],
        "acceptance_criteria": [
            {
                "id": "AC-GLOBAL-1",
                "criteria": "All features must work on latest Chrome, Firefox, Safari, and Edge browsers",
                "description": "Cross-browser compatibility requirement to ensure broad accessibility",
            },
            {
                "id": "AC-GLOBAL-2",
                "criteria": "Application must be fully responsive on mobile devices (320px+) and desktop (1024px+)",
                "description": "Mobile-first design requirement for optimal user experience across devices",
            },
            {
                "id": "AC-GLOBAL-3",
                "criteria": "Page load time must be under 2 seconds on 4G connection",
                "description": "Performance requirement to ensure good user experience",
            },
        ],
        "ui_multi_section": True,
        "ui_sections": 3,
        "assumptions": [
            "Users have valid email addresses for registration",
            "Email delivery service is configured and operational",
            "Users understand basic web navigation patterns",
        ],
        "out_of_scope": [
            "Social media login (OAuth) integration",
            "Two-factor authentication",
            "Password recovery via SMS",
        ],
    }


def build_architect_example() -> dict[str, Any]:
    """Create a realistic example for architect output with actual content."""
    return {
        "design_doc": """## System Overview
A modern web application following a 3-tier architecture with clear separation of concerns.

## Components
- **Frontend**: React SPA with TypeScript
- **Backend**: RESTful API server
- **Database**: Relational database for data persistence

## Data Flow
1. User interacts with frontend
2. Frontend makes API calls to backend
3. Backend processes requests and queries database
4. Responses flow back to frontend

## Security
- Authentication via JWT tokens
- Password hashing with bcrypt
- HTTPS for all communications""",
        "apis": [
            {
                "path": "/api/v1/users",
                "method": "GET",
                "description": "List all users with pagination",
                "request_schema": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                },
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "users": {"type": "array"},
                        "total": {"type": "integer"},
                    },
                },
            },
            {
                "path": "/api/v1/users",
                "method": "POST",
                "description": "Create a new user",
                "request_schema": {
                    "type": "object",
                    "required": ["email", "password"],
                    "properties": {
                        "email": {"type": "string"},
                        "password": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "email": {"type": "string"},
                        "created_at": {"type": "string"},
                    },
                },
            },
        ],
        "decisions": [
            {
                "decision": "Use JWT for authentication",
                "reason": "Stateless authentication enables horizontal scaling and works well with SPAs. Industry standard with good library support.",
                "tradeoffs": "Tokens cannot be easily revoked before expiration. Requires secure key management and HTTPS.",
            },
            {
                "decision": "RESTful API design",
                "reason": "Well-understood, widely supported, and easy to consume by various clients. Clear resource-based URL structure.",
                "tradeoffs": "May require multiple round trips for complex operations. Not as efficient as GraphQL for nested data.",
            },
        ],
        "next_tasks": [
            {
                "role": "Engineer",
                "task": "Implement user authentication API endpoints with JWT token generation and validation",
            },
            {
                "role": "Engineer",
                "task": "Set up database schema and migrations for user management",
            },
        ],
    }


def build_structured_messages(
    role_name: str,
    role_goal: str,
    constraints: list[str],
    sop_task: str,
    user_request: str,
    schema_name: str,
    schema: dict[str, Any],
    extra_context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Create chat messages instructing the LLM to output JSON only that conforms to schema."""
    constraints_text = "\n".join(f"- {c}" for c in constraints)

    # Use realistic examples for architect and PM, minimal for others
    is_architect = schema_name == "architect.schema.json"
    is_pm = schema_name == "pm_spec.schema.json"

    if is_architect:
        example = build_architect_example()
        example_note = """
IMPORTANT ARCHITECT GUIDELINES:
- APIs array must contain at least 3-5 REST endpoints covering main user stories
- Each API must have: path, method, description, request_schema, response_schema
- Decisions array must contain at least 2-3 key architectural choices
- Design doc must be comprehensive with markdown sections (##)
- Focus on practical, implementable designs

Example of a COMPLETE architect response:"""
    elif is_pm:
        example = build_pm_example()
        example_note = """
IMPORTANT PM GUIDELINES:
- Create 3-5+ user stories following "As a [user], I want [action], so that [benefit]" format
- Each user story must have 3-5 SPECIFIC, testable acceptance criteria
- Global acceptance criteria must be real requirements (e.g., "Support mobile devices 320px+")
- NEVER use placeholder text like "Criteria 1", "Criteria 2" - write ACTUAL criteria
- Acceptance criteria must be testable and verifiable
- Focus on user value and business outcomes

Example of a COMPLETE PM response:"""
    else:
        example = build_minimal_example_from_schema(schema)
        example_note = "\nMinimal example:"

    system = f"You are {role_name}.\nGoal: {role_goal}.\nConstraints:\n{constraints_text}\n\nYou MUST return STRICT JSON ONLY (no markdown, no commentary) conforming to the schema '{schema_name}'."

    if is_architect:
        system += "\n\nAs an architect, you must provide COMPLETE, DETAILED designs with actual content - empty arrays are NOT acceptable."
    elif is_pm:
        system += "\n\nAs a product manager, you must write REAL acceptance criteria with actual requirements - NEVER use generic placeholders like 'Criteria 1' or 'Criteria 2'."

    context_parts = [f"TASK: {sop_task}", f"USER_REQUEST: {user_request}"]
    if extra_context:
        with contextlib.suppress(Exception):
            context_parts.append(
                f"CONTEXT: {json.dumps(extra_context, ensure_ascii=False)}"
            )

    user = (
        "\n".join(context_parts)
        + "\nReturn JSON ONLY with COMPLETE content for all required fields."
        + example_note
        + f"\n{json.dumps(example, ensure_ascii=False, indent=2)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
