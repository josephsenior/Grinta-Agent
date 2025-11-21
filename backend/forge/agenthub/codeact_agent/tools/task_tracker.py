"""Structured task tracking tool definition for CodeAct runs."""

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from ._compat import build_tool_param

from forge.llm.tool_names import TASK_TRACKER_TOOL_NAME

_DETAILED_TASK_TRACKER_DESCRIPTION = "This tool provides structured task management capabilities for development workflows.\nIt enables systematic tracking of work items, progress monitoring, and efficient\norganization of complex development activities.\n\nThe tool maintains visibility into project status and helps communicate\nprogress effectively to users.\n\n## Application Guidelines\n\nUtilize this tool in the following situations:\n\n1. Multi-phase development work - When projects involve multiple sequential or\n   parallel activities\n2. Complex implementation tasks - Work requiring systematic planning and\n   coordination across multiple components\n3. Explicit user request for task organization - When users specifically ask\n   for structured task management\n4. Multiple concurrent requirements - When users present several work items\n   that need coordination\n5. Project initiation - Capture and organize user requirements at project start\n6. Work commencement - Update task status to in_progress before beginning\n   implementation. Maintain focus by limiting active work to one task\n7. Task completion - Update status to done and identify any additional work\n   that emerged during implementation\n\n## Situations Where Tool Usage Is Unnecessary\n\nAvoid using this tool when:\n\n1. Single atomic tasks that require no decomposition\n2. Trivial operations where tracking adds no organizational value\n3. Simple activities completable in minimal steps\n4. Pure information exchange or discussion\n\nNote: For single straightforward tasks, proceed with direct implementation\nrather than creating tracking overhead.\n\n## Usage Scenarios\n\n**Scenario A: Feature Development with Validation**\nUser request: \"Build a user authentication system with login/logout functionality.\nDon't forget to include input validation and error handling!\"\n\nResponse approach: I'll implement a user authentication system with comprehensive\nvalidation. Let me organize this work systematically.\n\n*Task breakdown includes:*\n1. Design authentication API endpoints and data models\n2. Implement user login/logout controllers with session management\n3. Add client-side form validation and error display\n4. Create backend input sanitization and security checks\n5. Implement comprehensive error handling for edge cases\n6. Perform integration testing and fix any issues\n\n**Scenario B: Codebase Refactoring**\nUser request: \"I need to update all instances of the method 'fetchData' to\n'retrieveInformation' throughout the entire project\"\n\nResponse approach: Let me first analyze your codebase to identify all locations\nwhere 'fetchData' appears.\n\n*After code analysis*\n\nI've located 12 occurrences of 'fetchData' across 6 files in your project.\nI'll create a systematic plan to update these references.\n\n*Organized task list includes specific file-by-file updates*\n\n**Scenario C: Multi-feature Development**\nUser request: \"Set up a blog platform with these components: admin dashboard,\narticle management, comment system, and user profiles.\"\n\nResponse approach: I'll help build your blog platform. Let me break down these\ncomponents into manageable implementation phases.\n\n*Creates structured plan with each feature decomposed into specific development tasks*\n\n## Counter-examples - Direct Implementation Preferred\n\n**Counter-example A: Simple inquiry**\nUser request: \"What's the syntax for a for loop in JavaScript?\"\n\nResponse approach: Here's how to write a for loop in JavaScript:\n\n```javascript\nfor (let i = 0; i < array.length; i++) {\n    console.log(array[i]);\n}\n```\n\n*No task tracking needed - single informational response*\n\n**Counter-example B: Minor modification**\nUser request: \"Please add a docstring to the processPayment function explaining\nits parameters.\"\n\nResponse approach: I'll add a docstring to explain the processPayment function.\n\n*Direct edit without task tracking for simple modification*\n\n## Status Management and Workflow\n\n1. **Status Values**: Track work using these states:\n   - todo: Not yet initiated\n   - in_progress: Currently active (maintain single focus)\n   - done: Successfully completed\n\n2. **Workflow Practices**:\n   - Update status dynamically as work progresses\n   - Mark completion immediately upon task finish\n   - Limit active work to ONE task at any given time\n   - Complete current activities before initiating new ones\n   - Remove obsolete tasks from tracking entirely\n\n3. **Completion Criteria**:\n   - Mark tasks as done only when fully achieved\n   - Keep status as in_progress if errors, blocks, or partial completion exist\n   - Create new tasks for discovered issues or dependencies\n   - Never mark done when:\n       - Test suites are failing\n       - Implementation remains incomplete\n       - Unresolved errors persist\n       - Required resources are unavailable\n\n4. **Task Organization**:\n   - Write precise, actionable descriptions\n   - Decompose complex work into manageable units\n   - Use descriptive, clear naming conventions\n\nWhen uncertain, favor using this tool. Proactive task management demonstrates\nsystematic approach and ensures comprehensive requirement fulfillment.\n"
_SHORT_TASK_TRACKER_DESCRIPTION = "Provides structured task management for development workflows, enabling progress\ntracking and systematic organization of complex coding activities.\n\n* Apply to multi-phase projects (3+ distinct steps) or when managing multiple user requirements\n* Update status (todo/in_progress/done) dynamically throughout work\n* Maintain single active task focus at any time\n* Mark completion immediately upon task finish\n* Decompose complex work into manageable, actionable units\n"


def create_task_tracker_tool(
    use_short_description: bool = False,
) -> ChatCompletionToolParam:
    """Create a task tracker tool for the agent.

    Args:
        use_short_description: Whether to use short or detailed description.

    Returns:
        ChatCompletionToolParam: The configured task tracker tool.

    """
    description = (
        _SHORT_TASK_TRACKER_DESCRIPTION
        if use_short_description
        else _DETAILED_TASK_TRACKER_DESCRIPTION
    )
    return build_tool_param(
        ChatCompletionToolParam,
        ChatCompletionToolParamFunctionChunk,
        name=TASK_TRACKER_TOOL_NAME,
        description=description,
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["view", "plan"],
                    "description": "The command to execute. `view` shows the current task list. `plan` creates or updates the task list based on provided requirements and progress. Always `view` the current list before making changes.",
                },
                "task_list": {
                    "type": "array",
                    "description": "The full task list. Required parameter of `plan` command.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Unique task identifier",
                            },
                            "title": {
                                "type": "string",
                                "description": "Brief task description",
                            },
                            "status": {
                                "type": "string",
                                "description": "Current task status",
                                "enum": ["todo", "in_progress", "done"],
                            },
                            "notes": {
                                "type": "string",
                                "description": "Optional additional context or details",
                            },
                        },
                        "required": ["title", "status", "id"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    )
