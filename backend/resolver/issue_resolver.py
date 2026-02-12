"""Runtime orchestration logic for resolving repository issues via agents."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import pathlib
import shutil
import subprocess
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from termcolor import colored

import backend
from backend.core.config import AgentConfig, ForgeConfig, SandboxConfig
from backend.core.config.utils import load_FORGE_config
from backend.core.logger import forge_logger as logger
from backend.core.main import create_runtime, run_controller
from backend.events.action import CmdRunAction, MessageAction
from backend.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    Observation,
)
from backend.events.stream import EventStreamSubscriber
from backend.integrations.service_types import ProviderType
from backend.models.llm_registry import LLMRegistry
from backend.resolver.issue_handler_factory import IssueHandlerFactory
from backend.resolver.resolver_output import ResolverOutput
from backend.resolver.utils import (
    codeact_user_response,
    get_unique_uid,
    identify_token,
    reset_logger_for_multiprocessing,
)
from backend.core.constants import GENERAL_TIMEOUT
from backend.utils.async_utils import call_async_from_sync

if TYPE_CHECKING:
    from argparse import Namespace

    from backend.controller.state.state import State
    from backend.events.event import Event
    from backend.resolver.interfaces.issue import Issue
    from backend.resolver.interfaces.issue_definitions import (
        ServiceContextIssue,
        ServiceContextPR,
    )
    from backend.runtime.base import Runtime

AGENT_CLASS = "Orchestrator"


class IssueResolver:
    """High-level orchestrator that clones repos, runs agents, and posts fixes."""

    def __init__(self, args: Namespace) -> None:
        """Initialize the IssueResolver with the given parameters."""
        # Parse repository information
        owner, repo = self._parse_repository(args.selected_repo)

        # Get authentication credentials
        token, username = self._get_credentials(args)

        # Identify platform
        platform = self._identify_platform(token, args.base_domain)

        # Load repository instruction
        repo_instruction = self._load_repo_instruction(args.repo_instruction_file)

        # Load prompt templates
        user_instructions_prompt_template, conversation_instructions_prompt_template = (
            self._load_prompt_templates(args)
        )

        # Determine base domain
        base_domain = self._determine_base_domain(args.base_domain, platform)

        # Initialize instance variables
        self._initialize_basic_properties(
            args,
            owner,
            repo,
            platform,
            args.issue_type,
            base_domain,
            repo_instruction,
            user_instructions_prompt_template,
            conversation_instructions_prompt_template,
        )

        # Create issue handler
        self.issue_handler = self._create_issue_handler(
            owner,
            repo,
            token,
            username,
            platform,
            base_domain,
            args.issue_type,
        )

    def _parse_repository(self, selected_repo: str) -> tuple[str, str]:
        """Parse repository string into owner and repo."""
        parts = selected_repo.rsplit("/", 1)
        if len(parts) < 2:
            msg = "Invalid repository format. Expected owner/repo"
            raise ValueError(msg)
        return parts[0], parts[1]

    def _get_credentials(self, args: Namespace) -> tuple[str, str]:
        """Get authentication token and username."""
        token = (
            args.token
            or os.getenv("GITHUB_TOKEN")
        )
        username = args.username or os.getenv("GIT_USERNAME")

        if not username:
            msg = "Username is required."
            raise ValueError(msg)
        if not token:
            msg = "Token is required."
            raise ValueError(msg)

        return token, username

    def _identify_platform(self, token: str, base_domain: str | None) -> ProviderType:
        """Identify the platform from the token."""
        return call_async_from_sync(identify_token, GENERAL_TIMEOUT, token, base_domain)

    def _load_repo_instruction(self, repo_instruction_file: str | None) -> str | None:
        """Load repository instruction from file if provided."""
        if not repo_instruction_file:
            return None

        with open(repo_instruction_file, encoding="utf-8") as f:
            return f.read()

    def _load_prompt_templates(self, args: Namespace) -> tuple[str, str]:
        """Load prompt templates for the issue type."""
        issue_type = args.issue_type
        prompt_file = args.prompt_file

        if prompt_file is None:
            prompt_file = self._get_default_prompt_file(issue_type)

        user_instructions_prompt_template = self._read_prompt_file(prompt_file)
        conversation_instructions_prompt_template = self._read_conversation_prompt_file(
            prompt_file
        )

        return (
            user_instructions_prompt_template,
            conversation_instructions_prompt_template,
        )

    def _get_default_prompt_file(self, issue_type: str) -> str:
        """Get default prompt file based on issue type."""
        if issue_type == "issue":
            return os.path.join(
                os.path.dirname(__file__), "prompts/resolve/basic-with-tests.jinja"
            )
        return os.path.join(
            os.path.dirname(__file__), "prompts/resolve/basic-followup.jinja"
        )

    def _read_prompt_file(self, prompt_file: str) -> str:
        """Read prompt template from file."""
        with open(prompt_file, encoding="utf-8") as f:
            return f.read()

    def _read_conversation_prompt_file(self, prompt_file: str) -> str:
        """Read conversation instructions prompt template."""
        conversation_prompt_file = prompt_file.replace(
            ".jinja", "-conversation-instructions.jinja"
        )
        return pathlib.Path(conversation_prompt_file).read_text()

    def _determine_base_domain(
        self, base_domain: str | None, platform: ProviderType
    ) -> str:
        """Determine the base domain for the git server."""
        if base_domain is not None:
            return base_domain

        return "github.com"

    def _initialize_basic_properties(
        self,
        args: Namespace,
        owner: str,
        repo: str,
        platform: ProviderType,
        issue_type: str,
        base_domain: str,
        repo_instruction: str | None,
        user_instructions_prompt_template: str,
        conversation_instructions_prompt_template: str,
    ) -> None:
        """Initialize basic instance properties."""
        self.output_dir = args.output_dir
        self.issue_type = issue_type
        self.issue_number = args.issue_number
        self.workspace_base = self.build_workspace_base(
            self.output_dir, self.issue_type, self.issue_number
        )
        self.max_iterations = args.max_iterations

        # Update Forge configuration
        self.app_config = self.update_FORGE_config(
            load_FORGE_config(),
            self.max_iterations,
            self.workspace_base,
            args.runtime,
        )

        # Set remaining properties
        self.owner = owner
        self.repo = repo
        self.platform = platform
        self.user_instructions_prompt_template = user_instructions_prompt_template
        self.conversation_instructions_prompt_template = (
            conversation_instructions_prompt_template
        )
        self.repo_instruction = repo_instruction
        self.comment_id = args.comment_id

    def _create_issue_handler(
        self,
        owner: str,
        repo: str,
        token: str,
        username: str,
        platform: ProviderType,
        base_domain: str,
        issue_type: str,
    ):
        """Create and return the issue handler."""
        factory = IssueHandlerFactory(
            owner=owner,
            repo=repo,
            token=token,
            username=username,
            platform=platform,
            base_domain=base_domain,
            issue_type=issue_type,
            llm_config=self.app_config.get_llm_config(),
        )
        return factory.create()

    @classmethod
    def update_FORGE_config(
        cls,
        config: ForgeConfig,
        max_iterations: int,
        workspace_base: str,
        runtime: str | None = None,
    ) -> ForgeConfig:
        """Mutate ForgeConfig with runtime/sandbox defaults appropriate for resolver."""
        config.default_agent = "Orchestrator"
        config.runtime = runtime or config.runtime or "local"
        config.max_budget_per_task = 4
        config.max_iterations = max_iterations
        config.agents = {"Orchestrator": AgentConfig(disabled_playbooks=["github"])}
        cls.update_sandbox_config(config)
        return config

    @classmethod
    def update_sandbox_config(
        cls,
        FORGE_config: ForgeConfig,
    ) -> None:
        """Update Forge configuration with sandbox settings.

        Args:
            FORGE_config: Configuration to update

        """
        sandbox_config = cls._create_sandbox_config()
        cls._apply_sandbox_config(FORGE_config, sandbox_config)

    @classmethod
    def _create_sandbox_config(cls) -> SandboxConfig:
        """Create sandbox configuration.

        Returns:
            Configured SandboxConfig

        """
        sandbox_config = SandboxConfig(
            enable_auto_lint=False,
            timeout=300,
        )

        return sandbox_config

    @classmethod
    def _apply_sandbox_config(
        cls, FORGE_config: ForgeConfig, sandbox_config: SandboxConfig
    ) -> None:
        """Apply sandbox configuration to Forge config.

        Args:
            FORGE_config: Configuration to update
            sandbox_config: Sandbox configuration to apply

        """
        FORGE_config.sandbox.enable_auto_lint = sandbox_config.enable_auto_lint
        FORGE_config.sandbox.timeout = sandbox_config.timeout
        FORGE_config.sandbox.runtime_startup_env_vars = (
            sandbox_config.runtime_startup_env_vars
        )
        FORGE_config.sandbox.browsergym_eval_env = sandbox_config.browsergym_eval_env

    def initialize_runtime(self, runtime: Runtime) -> None:
        """Initialize the runtime for the agent.

        This function is called before the runtime is used to run the agent.
        It sets up git configuration and runs the setup script if it exists.
        """
        logger.info("-" * 30)
        logger.info("BEGIN Runtime Completion Fn")
        logger.info("-" * 30)
        obs: Observation
        # Use runtime's workspace_root for cross-platform compatibility
        work_dir = str(runtime.workspace_root)
        action = CmdRunAction(command=f"cd {work_dir}")
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        if obs.__class__.__name__ != "CmdOutputObservation" or obs.exit_code != 0:
            msg = f"Failed to change directory to {work_dir}.\n{obs}"
            raise RuntimeError(msg)
        action = CmdRunAction(command='git config --global core.pager ""')
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        if obs.__class__.__name__ != "CmdOutputObservation" or obs.exit_code != 0:
            msg = f"Failed to set git config.\n{obs}"
            raise RuntimeError(msg)
        logger.info("Checking for .Forge/setup.sh script...")
        runtime.maybe_run_setup_script()
        logger.info("Checking for .Forge/pre-commit.sh script...")
        runtime.maybe_setup_git_hooks()

    def _run_command_with_validation(
        self, runtime: Runtime, command: str, error_message: str
    ) -> None:
        """Run a command and validate the result."""
        action = CmdRunAction(command=command)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})

        if obs.__class__.__name__ != "CmdOutputObservation" or obs.exit_code != 0:
            msg = f"{error_message}. Observation: {obs}"
            raise RuntimeError(msg)

    def _setup_git_config(self, runtime: Runtime) -> None:
        """Setup git configuration for the workspace."""
        self._run_command_with_validation(
            runtime, "cd /workspace", "Failed to change directory to /workspace"
        )

        self._run_command_with_validation(
            runtime, 'git config --global core.pager ""', "Failed to set git config"
        )

        self._run_command_with_validation(
            runtime,
            "git config --global --add safe.directory /workspace",
            "Failed to set git config",
        )

    def _stage_changes(self, runtime: Runtime) -> None:
        """Stage all changes using git add."""
        command = "git add -A"

        self._run_command_with_validation(runtime, command, "Failed to git add")

    async def _get_git_patch_with_retry(
        self, runtime: Runtime, base_commit: str
    ) -> str | None:
        """Get git patch with retry logic."""
        n_retries = 0
        git_patch = None

        while n_retries < 5:
            action = CmdRunAction(command=f"git diff --no-color --cached {base_commit}")
            action.set_hard_timeout(600 + 100 * n_retries)
            logger.info(action, extra={"msg_type": "ACTION"})
            obs = runtime.run_action(action)
            logger.info(obs, extra={"msg_type": "OBSERVATION"})
            n_retries += 1

            if obs.__class__.__name__ == "CmdOutputObservation":
                if obs.exit_code == 0:
                    git_patch = obs.content.strip()
                    break
                logger.info("Failed to get git diff, retrying...")
                await asyncio.sleep(10)
            elif isinstance(obs, ErrorObservation):
                logger.error("Error occurred: %s. Retrying...", obs.content)
                await asyncio.sleep(10)
            else:
                msg = f"Unexpected observation type: {type(obs)}"
                raise ValueError(msg)

        return git_patch

    def _log_completion_boundary(self, message: str) -> None:
        """Log completion function boundary."""
        logger.info("-" * 30)
        logger.info(message)
        logger.info("-" * 30)

    async def complete_runtime(
        self, runtime: Runtime, base_commit: str
    ) -> dict[str, Any]:
        """Complete the runtime for the agent.

        This function is called before the runtime is used to run the agent.
        If you need to do something in the sandbox to get the correctness metric after
        the agent has run, modify this function.
        """
        self._log_completion_boundary("BEGIN Runtime Completion Fn")

        # Setup git configuration
        self._setup_git_config(runtime)

        # Stage changes
        self._stage_changes(runtime)

        # Get git patch with retry logic
        git_patch = await self._get_git_patch_with_retry(runtime, base_commit)

        self._log_completion_boundary("END Runtime Completion Fn")
        return {"git_patch": git_patch}

    @staticmethod
    def build_workspace_base(
        output_dir: str, issue_type: str, issue_number: int
    ) -> str:
        """Construct absolute workspace path for a specific issue run."""
        workspace_base = os.path.join(
            output_dir, "workspace", f"{issue_type}_{issue_number}"
        )
        return os.path.abspath(workspace_base)

    async def process_issue(
        self,
        issue: Issue,
        base_commit: str,
        issue_handler: ServiceContextIssue | ServiceContextPR,
        reset_logger: bool = False,
    ) -> ResolverOutput:
        """Process an issue by running the agent and generating a patch.

        Args:
            issue: The issue to process
            base_commit: Base git commit SHA
            issue_handler: Handler for the issue/PR
            reset_logger: Whether to reset the logger

        Returns:
            ResolverOutput containing results

        """
        self._setup_logging(issue, reset_logger)
        runtime = await self._setup_runtime()

        # Get instruction and run agent
        instruction, conversation_instructions, images_urls = self._get_instruction(
            issue, issue_handler
        )
        state, last_error = await self._run_agent(
            instruction, images_urls, conversation_instructions, runtime
        )

        # Complete and get results
        return_val = await self.complete_runtime(runtime, base_commit)
        git_patch = return_val["git_patch"]
        logger.info(
            "Got git diff for instance %s:\n--------\n%s\n--------",
            issue.number,
            git_patch,
        )

        # Build output
        return self._build_resolver_output(
            issue, issue_handler, instruction, base_commit, git_patch, state, last_error
        )

    def _setup_logging(self, issue: Issue, reset_logger: bool) -> None:
        """Setup logging for issue processing.

        Args:
            issue: Issue being processed
            reset_logger: Whether to reset the logger

        """
        if reset_logger:
            log_dir = os.path.join(self.output_dir, "infer_logs")
            reset_logger_for_multiprocessing(logger, str(issue.number), log_dir)
        else:
            logger.info("Starting fixing issue %s.", issue.number)

    async def _setup_runtime(self):
        """Setup and prepare the runtime environment.

        Returns:
            Configured runtime instance

        """
        # Clean and copy workspace
        if os.path.exists(self.workspace_base):
            shutil.rmtree(self.workspace_base)
        shutil.copytree(os.path.join(self.output_dir, "repo"), self.workspace_base)

        # Create and connect runtime
        llm_registry = LLMRegistry(self.app_config)
        runtime = create_runtime(
            self.app_config,
            llm_registry,
            workspace_base=self.workspace_base,
        )
        await runtime.connect()

        # Subscribe to events
        def on_event(evt: Event) -> None:
            """Log runtime events as they stream in."""
            logger.info(evt)

        event_stream = runtime.event_stream
        if event_stream is not None:
            event_stream.subscribe(
                EventStreamSubscriber.MAIN, on_event, str(uuid4())
            )
        else:
            logger.warning("Runtime event stream unavailable; skipping subscription")

        self.initialize_runtime(runtime)
        return runtime

    def _get_instruction(self, issue: Issue, issue_handler):
        """Get instruction for the issue.

        Args:
            issue: Issue to process
            issue_handler: Handler for the issue

        Returns:
            Tuple of (instruction, conversation_instructions, images_urls)

        """
        return issue_handler.get_instruction(
            issue,
            self.user_instructions_prompt_template,
            self.conversation_instructions_prompt_template,
            self.repo_instruction,
        )

    async def _run_agent(
        self, instruction: str, images_urls, conversation_instructions, runtime
    ):
        """Run the agent with the given instruction.

        Args:
            instruction: Instruction text
            images_urls: List of image URLs
            conversation_instructions: Conversation setup instructions
            runtime: Runtime instance

        Returns:
            Tuple of (state, last_error)

        """
        action = MessageAction(content=instruction, image_urls=images_urls)
        last_error = None

        try:
            state: State | None = await run_controller(
                config=self.app_config,
                initial_user_action=action,
                runtime=runtime,
                fake_user_response_fn=codeact_user_response,
                conversation_instructions=conversation_instructions,
            )
            if state is None:
                msg = "Failed to run the agent."
                raise RuntimeError(msg)
        except (ValueError, RuntimeError) as e:
            error_msg = "Agent failed to run or crashed"
            logger.error("%s: %s", error_msg, e)
            state = None
            last_error = error_msg

        return state, last_error

    def _build_resolver_output(
        self,
        issue: Issue,
        issue_handler,
        instruction: str,
        base_commit: str,
        git_patch: str,
        state: State | None,
        last_error: str | None,
    ) -> ResolverOutput:
        """Build resolver output from processing results.

        Args:
            issue: Processed issue
            issue_handler: Issue handler
            instruction: Original instruction
            base_commit: Base commit SHA
            git_patch: Generated git patch
            state: Agent state (or None if failed)
            last_error: Error message if agent failed

        Returns:
            ResolverOutput object

        """
        if state is None:
            return ResolverOutput(
                issue=issue,
                issue_type=issue_handler.issue_type,
                instruction=instruction,
                base_commit=base_commit,
                git_patch=git_patch,
                history=[],
                metrics=None,
                success=False,
                comment_success=None,
                result_explanation="Agent failed to run",
                error=last_error or "Agent failed to run or crashed",
            )

        histories = [dataclasses.asdict(event) for event in state.history]
        metrics = state.metrics.get() if state.metrics else None
        success, comment_success, result_explanation = issue_handler.guess_success(
            issue, state.history, git_patch
        )

        # Log PR success details if applicable
        if issue_handler.issue_type == "pr" and comment_success:
            self._log_pr_success(comment_success, result_explanation)

        return ResolverOutput(
            issue=issue,
            issue_type=issue_handler.issue_type,
            instruction=instruction,
            base_commit=base_commit,
            git_patch=git_patch,
            history=histories,
            metrics=metrics,
            success=success,
            comment_success=comment_success,
            result_explanation=result_explanation,
            error=state.last_error or None,
        )

    def _log_pr_success(self, comment_success: list, result_explanation: str) -> None:
        """Log PR success details.

        Args:
            comment_success: List of success indicators
            result_explanation: JSON explanation of results

        """
        success_log = "I have updated the PR and resolved some of the issues that were cited in the pull request review. Specifically, I identified the following revision requests, and all the ones that I think I successfully resolved are checked off. All the unchecked ones I was not able to resolve, so manual intervention may be required:\n"

        try:
            explanations = json.loads(result_explanation)
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse result_explanation as JSON: %s", result_explanation
            )
            explanations = [str(result_explanation)]

        for success_indicator, explanation in zip(comment_success, explanations):
            status = (
                colored("[X]", "red") if success_indicator else colored("[ ]", "red")
            )
            bullet_point = colored("-", "yellow")
            success_log += f"\n{bullet_point} {status}: {explanation}"

        logger.info(success_log)

    def extract_issue(self) -> Issue:
        """Retrieve the target issue/PR instance using the configured handler."""
        if issues := self.issue_handler.get_converted_issues(
            issue_numbers=[self.issue_number],
            comment_id=self.comment_id,
        ):
            return issues[0]
        msg = f"No issues found for issue number {
            self.issue_number
        }. Please verify that:\n1. The issue/PR #{
            self.issue_number
        } exists in the repository {self.owner}/{
            self.repo
        }\n2. You have the correct permissions to access it\n3. The repository name is spelled correctly"
        raise ValueError(
            msg,
        )

    async def resolve_issue(self, reset_logger: bool = False) -> None:
        """Resolve a single issue.

        Args:
            reset_logger: Whether to reset the logger for multiprocessing.

        """
        issue = self.extract_issue()
        self._validate_comment_id(issue)

        self._get_model_name()
        self._setup_output_directories()
        repo_dir = self._setup_repository()
        base_commit = self._get_base_commit(repo_dir)
        self._load_repo_instructions(repo_dir)

        output_file = self._get_output_file_path()
        if self._is_issue_already_processed(output_file):
            return

        await self._process_issue_with_output(
            issue, base_commit, repo_dir, output_file, reset_logger
        )

    def _validate_comment_id(self, issue) -> None:
        """Validate comment ID if specified."""
        if self.comment_id is not None:
            if (
                self.issue_type == "pr"
                and (not issue.review_comments)
                and (not issue.review_threads)
                and (not issue.thread_comments)
            ):
                msg = f"Comment ID {self.comment_id} did not have a match for issue {issue.number}"
                raise ValueError(msg)
            if self.issue_type == "issue" and (not issue.thread_comments):
                msg = f"Comment ID {self.comment_id} did not have a match for issue {issue.number}"
                raise ValueError(msg)

    def _get_model_name(self) -> str:
        """Get model name from config."""
        return self.app_config.get_llm_config().model.split("/")[-1]

    def _setup_output_directories(self) -> None:
        """Set up output directories."""
        pathlib.Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        pathlib.Path(os.path.join(self.output_dir, "infer_logs")).mkdir(
            parents=True, exist_ok=True
        )
        logger.info("Using output directory: %s", self.output_dir)

    def _setup_repository(self) -> str:
        """Set up repository directory."""
        repo_dir = os.path.join(self.output_dir, "repo")
        if not os.path.exists(repo_dir):
            self._clone_repository(repo_dir)
        return repo_dir

    def _clone_repository(self, repo_dir: str) -> None:
        """Clone the repository."""
        checkout_output = subprocess.check_output(
            [
                "git",
                "clone",
                self.issue_handler.get_clone_url(),
                f"{self.output_dir}/repo",
            ],
        ).decode("utf-8")
        if "fatal" in checkout_output:
            msg = f"Failed to clone repository: {checkout_output}"
            raise RuntimeError(msg)

    def _get_base_commit(self, repo_dir: str) -> str:
        """Get base commit hash."""
        base_commit = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir)
            .decode("utf-8")
            .strip()
        )
        logger.info("Base commit: %s", base_commit)
        return base_commit

    def _load_repo_instructions(self, repo_dir: str) -> None:
        """Load repository instructions if available."""
        if self.repo_instruction is None:
            FORGE_instructions_path = os.path.join(repo_dir, ".FORGE_instructions")
            if os.path.exists(FORGE_instructions_path):
                with open(FORGE_instructions_path, encoding="utf-8") as f:
                    self.repo_instruction = f.read()

    def _get_output_file_path(self) -> str:
        """Get output file path."""
        output_file = os.path.join(self.output_dir, "output.jsonl")
        logger.info("Writing output to %s", output_file)
        return output_file

    def _is_issue_already_processed(self, output_file: str) -> bool:
        """Check if issue was already processed."""
        if os.path.exists(output_file):
            with open(output_file, encoding="utf-8") as f:
                for line in f:
                    payload = json.loads(line)
                    issue_payload = payload.get("issue") if isinstance(payload, dict) else None
                    issue_number = None
                    if isinstance(issue_payload, dict):
                        issue_number = issue_payload.get("number")
                    if issue_number == self.issue_number:
                        logger.warning(
                            "Issue %s was already processed. Skipping.",
                            self.issue_number,
                        )
                        return True
        return False

    async def _process_issue_with_output(
        self,
        issue,
        base_commit: str,
        repo_dir: str,
        output_file: str,
        reset_logger: bool,
    ) -> None:
        """Process issue and write output."""
        output_fp = open(output_file, "a", encoding="utf-8")
        model_name = self._get_model_name()
        logger.info(
            "Resolving issue %s with Agent %s, model %s, max iterations %s.",
            self.issue_number,
            AGENT_CLASS,
            model_name,
            self.max_iterations,
        )

        try:
            if self.issue_type == "pr":
                base_commit = self._handle_pr_branch(issue, repo_dir)

            output = await self.process_issue(
                issue, base_commit, self.issue_handler, reset_logger
            )
            from backend.core.pydantic_compat import model_dump_json

            output_fp.write(model_dump_json(output) + "\n")
            output_fp.flush()
        finally:
            output_fp.close()
            logger.info("Finished.")

    def _handle_pr_branch(self, issue, repo_dir: str) -> str:
        """Handle PR branch checkout."""
        branch_to_use = issue.head_branch
        logger.info(
            "Checking out to PR branch %s for issue %s", branch_to_use, issue.number
        )

        if not branch_to_use:
            msg = "Branch name cannot be None"
            raise ValueError(msg)

        fetch_cmd = ["git", "fetch", "origin", branch_to_use]
        subprocess.check_output(fetch_cmd, cwd=repo_dir)

        checkout_cmd = ["git", "checkout", branch_to_use]
        subprocess.check_output(checkout_cmd, cwd=repo_dir)

        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir)
            .decode("utf-8")
            .strip()
        )

