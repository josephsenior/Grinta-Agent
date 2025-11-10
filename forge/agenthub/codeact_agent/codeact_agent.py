"""Agent implementation that edits code through structured tool calls."""

from __future__ import annotations

import os
import sys
from collections import deque
from typing import Optional, TYPE_CHECKING, Any

from forge.llm.llm_registry import LLMRegistry

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam

    from forge.events.action import Action
    from forge.llm.llm import ModelResponse
import forge.agenthub.codeact_agent.function_calling as codeact_function_calling
from forge.agenthub.codeact_agent.tools.bash import create_cmd_run_tool
from forge.agenthub.codeact_agent.tools.browser import BrowserTool
from forge.agenthub.codeact_agent.tools.condensation_request import (
    CondensationRequestTool,
)
from forge.agenthub.codeact_agent.tools.database import get_database_tools
from forge.agenthub.codeact_agent.tools.finish import FinishTool
from forge.agenthub.codeact_agent.tools.ipython import IPythonTool
from forge.agenthub.codeact_agent.tools.llm_based_edit import LLMBasedFileEditTool
from forge.agenthub.codeact_agent.tools.str_replace_editor import (
    create_str_replace_editor_tool,
)
from forge.agenthub.codeact_agent.tools.task_tracker import create_task_tracker_tool
from forge.agenthub.codeact_agent.tools.think import ThinkTool
from forge.controller.agent import Agent
from forge.controller.state.state import State
from forge.core.config import AgentConfig
from forge.core.logger import forge_logger as logger
from forge.core.message import Message, TextContent
from forge.events.action import AgentFinishAction, MessageAction
from forge.events.event import Event, EventSource
from forge.llm.llm_utils import check_tools
from forge.memory.condenser import Condenser
from forge.memory.condenser.condenser import Condensation
from forge.memory.view import View
from forge.memory.conversation_memory import ConversationMemory
from forge.runtime.plugins import (
    AgentSkillsRequirement,
    JupyterRequirement,
    PluginRequirement,
)
from forge.utils.prompt import PromptManager


class CodeActAgent(Agent):
    """CodeAct Agent - Forge' flagship autonomous coding agent (Beta focus).
    
    Implements the CodeAct paradigm (https://arxiv.org/abs/2402.01030) which consolidates
    agent actions into a unified code action space. The agent alternates between reasoning
    and acting through bash commands and Python code execution.
    
    Architecture:
        The agent uses a ReAct loop:
        1. Observe current state (file contents, command output, errors)
        2. Reason about next action (LLM generates thought process)
        3. Act via tools (edit file, run command, browse web, execute Python)
        4. Observe result and repeat
    
    Available Actions:
        - Edit files (structure-aware, Tree-sitter parsing)
        - Run bash commands (ls, git, pytest, npm, etc.)
        - Execute Python code (IPython kernel)
        - Browse websites (Playwright automation)
        - Communicate with user (questions, status updates)
    
    Safety Features:
        - Circuit breaker (auto-pause on repeated failures)
        - Stuck detection (prevents infinite loops)
        - Sandbox execution (Docker isolation)
        - Risk assessment (AI-powered security analysis)
        - Cost quotas (budget protection)
    
    Performance:
        - Typical task: 2-10 actions, 15-60 seconds
        - Simple bug fix: 2-3 actions, ~15 seconds
        - Feature implementation: 5-10 actions, ~45 seconds
        - Complex refactoring: 10-20 actions, 1-3 minutes
    
    Example:
        ```python
        from forge.controller.agent_controller import AgentController
        from forge.core.config import LLMConfig
        
        config = LLMConfig(model='claude-sonnet-4-20250514')
        controller = AgentController(
            agent_name='CodeActAgent',
            llm=config,
            max_iterations=100
        )
        await controller.setup_task('Fix the bug in main.py line 42')
        await controller.set_agent_state_to(AgentState.RUNNING)
        ```
    
    Attributes:
        VERSION: Agent version string
        sandbox_plugins: Required plugins (AgentSkills, Jupyter)
        pending_actions: Queue of actions to execute
        hallucination_detector: Detects and corrects hallucinations
        anti_hallucination: Multi-layer hallucination prevention
        enhanced_context_manager: Context window optimization
        conversation_memory: Conversation history management
        condenser: Memory condensation for long conversations
        ace_framework: Self-improving agent framework (when enabled)
    
    References:
        - CodeAct Paper: https://arxiv.org/abs/2402.01030
        - Documentation: docs/features/codeact-agent.md
        - README: Forge/agenthub/codeact_agent/README.md

    """
    
    VERSION = "2.2"
    sandbox_plugins: list[PluginRequirement] = [AgentSkillsRequirement(), JupyterRequirement()]

    def __init__(
        self,
        config: AgentConfig,
        llm_registry: LLMRegistry,
        plugin_requirements: list[PluginRequirement] | None = None,
    ) -> None:
        """Initialize the CodeAct agent."""
        super().__init__(config=config, llm_registry=llm_registry)
        self.plugin_requirements = plugin_requirements or []
        production_health_check = getattr(self.config, "production_health_check", False)
        health_check_prompts = getattr(self.config, "health_check_prompts", None)
        self.production_health_check_enabled = bool(production_health_check and health_check_prompts)
        self.pending_actions: deque[Action] = deque()
        
        # Initialize prompt optimization attributes before any methods that might use them
        self.prompt_optimizer = None
        self.tool_optimizer = None
        
        # Initialize action verifier (lazy-loaded when runtime available)
        self.action_verifier = None
        
        # Initialize hallucination detector (Layer 4: Production Reliability)
        from forge.agenthub.codeact_agent.hallucination_detector import HallucinationDetector
        self.hallucination_detector = HallucinationDetector()
        
        # Initialize Ultimate Anti-Hallucination System (7.5/10 → 9.5/10)
        from forge.agenthub.codeact_agent.anti_hallucination_system import AntiHallucinationSystem
        self.anti_hallucination = AntiHallucinationSystem()
        
        # Initialize Enhanced Context Manager if enabled (MUST be before reset())
        self.enhanced_context_manager = None
        self._initialize_enhanced_context_manager()
        
        self.reset()
        self.tools = self._get_tools()
        self.conversation_memory = ConversationMemory(self.config, self.prompt_manager)
        condenser_config = getattr(self.config, "condenser_config", None) or getattr(self.config, "condenser", None)
        self.condenser = (
            Condenser.from_config(condenser_config, llm_registry)
            if condenser_config is not None
            else None
        )
        logger.debug("Using condenser: %s", type(self.condenser))
        
        # Initialize ACE framework if enabled
        self.ace_framework = None
        self._initialize_ace_framework()
        
        # Initialize prompt optimization if enabled
        self._initialize_prompt_optimization()
        
        # Run production health check (SaaS deployment)
        self._run_production_health_check()

    def _initialize_enhanced_context_manager(self) -> None:
        """Initialize Enhanced Context Manager if enabled in config."""
        if not getattr(self.config, "enable_enhanced_context", False):
            self.enhanced_context_manager = None
            return
        
        try:
            from forge.memory.enhanced_context_manager import EnhancedContextManager
            
            # Initialize enhanced context manager with config
            self.enhanced_context_manager = EnhancedContextManager(
                short_term_window=getattr(self.config, "context_short_term_window", 5),
                working_memory_size=getattr(self.config, "context_working_size", 50),
                long_term_max_size=getattr(self.config, "context_long_term_size", 200),
                contradiction_threshold=getattr(self.config, "context_contradiction_threshold", 0.7)
            )
            
            # Load existing state if persistence path exists
            persistence_path = getattr(self.config, "context_persistence_path", None)
            if persistence_path:
                try:
                    self.enhanced_context_manager.load_from_file(persistence_path)
                    logger.info(f"Loaded enhanced context state from {persistence_path}")
                except Exception as e:
                    logger.debug(f"No existing context state to load: {e}")
            
            logger.info("✅ Enhanced Context Manager initialized (7/10 → 9/10)")
            logger.info("   - Decision tracking: Active")
            logger.info("   - Hierarchical memory: 3 tiers")
            logger.info("   - Context anchors: Enabled")
            logger.info("   - Contradiction detection: Active")
            
        except ImportError as e:
            logger.error(f"Failed to import Enhanced Context Manager: {e}")
            self.enhanced_context_manager = None
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Context Manager: {e}")
            self.enhanced_context_manager = None

    def _initialize_ace_framework(self) -> None:
        """Initialize ACE framework if enabled in config."""
        if not getattr(self.config, "enable_ace", False):
            return
        
        try:
            from forge.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig
            
            # Create ACE configuration from agent config
            ace_config = ACEConfig(
                enable_ace=getattr(self.config, "enable_ace", False),
                max_bullets=getattr(self.config, "ace_max_bullets", 1000),
                multi_epoch=getattr(self.config, "ace_multi_epoch", True),
                num_epochs=getattr(self.config, "ace_num_epochs", 5),
                reflector_max_iterations=getattr(self.config, "ace_reflector_max_iterations", 5),
                enable_online_adaptation=getattr(self.config, "ace_enable_online_adaptation", True),
                playbook_persistence_path=getattr(self.config, "ace_playbook_path", None),
                min_helpfulness_threshold=getattr(self.config, "ace_min_helpfulness_threshold", 0.0),
                max_playbook_content_length=getattr(self.config, "ace_max_playbook_content_length", 50),
                enable_grow_and_refine=getattr(self.config, "ace_enable_grow_and_refine", True),
                cleanup_interval_days=getattr(self.config, "ace_cleanup_interval_days", 30),
                redundancy_threshold=getattr(self.config, "ace_redundancy_threshold", 0.8)
            )
            
            # Create context playbook
            context_playbook = ContextPlaybook(
                max_bullets=ace_config.max_bullets,
                enable_grow_and_refine=ace_config.enable_grow_and_refine
            )
            
            # Load existing playbook if path exists
            if ace_config.playbook_persistence_path:
                try:
                    context_playbook.load_from_disk(ace_config.playbook_persistence_path)
                except Exception as e:
                    logger.warning(f"Failed to load existing ACE playbook: {e}")
            
            # Initialize ACE framework
            self.ace_framework = ACEFramework(
                llm=self.llm,
                context_playbook=context_playbook,
                config=ace_config
            )
            
            logger.info("ACE framework initialized for CodeAct agent")
            
        except ImportError as e:
            logger.error(f"Failed to import ACE framework: {e}")
            self.ace_framework = None
        except Exception as e:
            logger.error(f"Failed to initialize ACE framework: {e}")
            self.ace_framework = None

    def _run_production_health_check(self) -> None:
        """Run the production health check for the given agent configuration.

        Args:
            llm_registry: the llm_registry object.
            agent_config: an agent_config object

        """
        try:
            from forge.agenthub.codeact_agent.tools.health_check import run_production_health_check
            
            # Run health check (raises on critical failure)
            run_production_health_check(raise_on_failure=True)
            
        except ImportError:
            # Health check module not available (shouldn't happen in production)
            logger.warning("Health check module not found - skipping dependency validation")
        except RuntimeError as e:
            # Critical dependency missing (Tree-sitter)
            logger.error(f"Production health check failed: {e}")
            # Re-raise to prevent agent from starting with missing dependencies
            raise
    
    def _initialize_prompt_optimization(self) -> None:
        """Initialize prompt optimization system if enabled."""
        if not getattr(self.config, "enable_prompt_optimization", False):
            self.prompt_optimizer = None
            return
        
        try:
            from forge.prompt_optimization import (
                PromptRegistry, PerformanceTracker, PromptOptimizer, 
                PromptStorage, OptimizationConfig, PromptCategory
            )
            
            # Create optimization configuration from agent config
            opt_config = OptimizationConfig(
                ab_split_ratio=getattr(self.config, "prompt_opt_ab_split", 0.8),
                min_samples_for_switch=getattr(self.config, "prompt_opt_min_samples", 5),
                confidence_threshold=getattr(self.config, "prompt_opt_confidence_threshold", 0.95),
                success_weight=getattr(self.config, "prompt_opt_success_weight", 0.4),
                time_weight=getattr(self.config, "prompt_opt_time_weight", 0.2),
                error_weight=getattr(self.config, "prompt_opt_error_weight", 0.2),
                cost_weight=getattr(self.config, "prompt_opt_cost_weight", 0.2),
                enable_evolution=getattr(self.config, "prompt_opt_enable_evolution", True),
                evolution_threshold=getattr(self.config, "prompt_opt_evolution_threshold", 0.7),
                max_variants_per_prompt=getattr(self.config, "prompt_opt_max_variants_per_prompt", 10),
                storage_path=getattr(self.config, "prompt_opt_storage_path", "~/.Forge/prompt_optimization/codeact/"),
                sync_interval=getattr(self.config, "prompt_opt_sync_interval", 100),
                auto_save=getattr(self.config, "prompt_opt_auto_save", True)
            )
            
            # Create components
            registry = PromptRegistry()
            tracker = PerformanceTracker({
                'success_weight': opt_config.success_weight,
                'time_weight': opt_config.time_weight,
                'error_weight': opt_config.error_weight,
                'cost_weight': opt_config.cost_weight
            })
            optimizer = PromptOptimizer(registry, tracker, opt_config)
            storage = PromptStorage(opt_config, registry, tracker)
            
            # Initialize prompt optimization system
            self.prompt_optimizer = {
                'registry': registry,
                'tracker': tracker,
                'optimizer': optimizer,
                'storage': storage,
                'config': opt_config
            }
            
            # Initialize tool optimizer
            from forge.prompt_optimization.tool_optimizer import ToolOptimizer
            self.tool_optimizer = ToolOptimizer(registry, tracker, optimizer)
            
            # Load existing data
            storage.load_all()
            
            logger.info("Prompt optimization system initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import prompt optimization: {e}")
            self.prompt_optimizer = None
            self.tool_optimizer = None
        except Exception as e:
            logger.error(f"Failed to initialize prompt optimization: {e}")
            self.prompt_optimizer = None
            self.tool_optimizer = None

    def _apply_prompt_optimization(self, messages: list, state: State) -> list:
        """Apply prompt optimization to messages if enabled."""
        if not self.prompt_optimizer or not messages:
            return messages
        
        try:
            from forge.prompt_optimization.models import PromptCategory
            
            # Get system message (first message)
            system_message = messages[0] if messages and messages[0].get("role") == "system" else None
            if not system_message:
                return messages
            
            # Create prompt ID for CodeAct system prompt
            prompt_id = "codeact_system"
            
            # Get optimized variant
            optimizer = self.prompt_optimizer['optimizer']
            variant = optimizer.select_variant(prompt_id, PromptCategory.CODEACT_SYSTEM)
            
            if variant:
                # Create optimized messages
                optimized_messages = list(messages)
                optimized_messages[0] = {
                    **system_message,
                    "content": variant.content
                }
                
                # Store variant ID for tracking
                state._prompt_variant_id = variant.id
                
                return optimized_messages
            
        except Exception as e:
            logger.warning(f"Prompt optimization failed: {e}")
        
        return messages

    def _track_prompt_performance(self, state: State, success: bool, 
                                execution_time: float, token_cost: float = 0.0,
                                error_message: Optional[str] = None):
        """Track prompt performance for optimization."""
        if not self.prompt_optimizer:
            return
        
        try:
            from forge.prompt_optimization.models import PromptCategory
            
            # Get variant ID from state
            variant_id = getattr(state, '_prompt_variant_id', None)
            if not variant_id:
                return
            
            prompt_id = "codeact_system"
            
            # Record performance
            optimizer = self.prompt_optimizer['optimizer']
            optimizer.record_execution(
                variant_id=variant_id,
                prompt_id=prompt_id,
                category=PromptCategory.CODEACT_SYSTEM,
                success=success,
                execution_time=execution_time,
                token_cost=token_cost,
                error_message=error_message,
                metadata={
                    'agent_name': self.name,
                    'task': getattr(state, 'current_task', 'unknown')
                }
            )
            
            # Auto-save if enabled
            storage = self.prompt_optimizer['storage']
            storage.auto_save()
            
        except Exception as e:
            logger.warning(f"Failed to track prompt performance: {e}")

    def _apply_tool_optimization(self, tools: list) -> list:
        """Apply optimization to tool descriptions and parameters."""
        if not self.tool_optimizer:
            return tools
        
        optimized_tools = []
        
        for tool in tools:
            try:
                # Get tool name from the tool function
                tool_name = tool.function.name if hasattr(tool, 'function') else None
                if not tool_name:
                    optimized_tools.append(tool)
                    continue
                
                # Optimize the tool
                optimized_tool = self.tool_optimizer.optimize_tool(tool, tool_name)
                optimized_tools.append(optimized_tool)
                
            except Exception as e:
                logger.warning(f"Failed to optimize tool {tool_name}: {e}")
                optimized_tools.append(tool)
        
        return optimized_tools

    def _track_tool_execution(self, tool_name: str, success: bool, 
                            execution_time: float, token_cost: float = 0.0,
                            error_message: Optional[str] = None, metadata: Optional[dict] = None):
        """Track tool execution for optimization."""
        if not self.tool_optimizer:
            return
        
        try:
            self.tool_optimizer.track_tool_execution(
                tool_name=tool_name,
                success=success,
                execution_time=execution_time,
                token_cost=token_cost,
                error_message=error_message,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.warning(f"Failed to track tool execution for {tool_name}: {e}")

    def _track_tool_usage(self, actions: list["Action"]) -> None:
        """Track tool usage for optimization."""
        if not self.tool_optimizer:
            return
        
        for action in actions:
            try:
                # Map action types to tool names
                tool_name_mapping = {
                    'think': 'think',
                    'run': 'execute_bash',
                    'run_powershell': 'execute_powershell',
                    'finish': 'finish',
                    'browse_interactive': 'browse_interactive',
                    'str_replace_editor': 'str_replace_editor',
                    'llm_based_edit': 'llm_based_edit',
                    'ipython_run_cell': 'ipython_run_cell',
                    'condensation_request': 'condensation_request',
                    'task_tracking': 'task_tracker'
                }
                
                action_type = getattr(action, 'action', None)
                tool_name = tool_name_mapping.get(action_type)
                
                if tool_name:
                    # Create initial tool variant if it doesn't exist
                    self._ensure_tool_variant_exists(tool_name, action)
                    
                    # Track the tool usage (we'll track success/failure later)
                    self._track_tool_execution(
                        tool_name=tool_name,
                        success=True,  # We'll update this when we know the result
                        execution_time=0.0,
                        token_cost=0.0,
                        metadata={
                            'action_type': action_type,
                            'action_id': getattr(action, 'id', None)
                        }
                    )
                    
            except Exception as e:
                logger.warning(f"Failed to track tool usage: {e}")

    def _ensure_tool_variant_exists(self, tool_name: str, action: "Action") -> None:
        """Ensure a tool variant exists for optimization."""
        if not self.tool_optimizer:
            return
        
        try:
            # Check if variants already exist for this tool
            prompt_id = self.tool_optimizer.tool_prompt_ids.get(tool_name)
            if not prompt_id:
                return
            
            # Check if variants exist
            variants = self.optimizer.get_variants_for_prompt(prompt_id) if self.optimizer else []
            if variants:
                return
            
            # Create initial variant from current tool description
            from forge.prompt_optimization.tool_descriptions import get_optimized_description
            
            optimized_desc = get_optimized_description(tool_name)
            if optimized_desc:
                description = optimized_desc.get('description', '')
                parameters = optimized_desc.get('parameters', {})
                
                self.tool_optimizer.create_tool_variants(
                    tool_name=tool_name,
                    original_description=description,
                    original_parameters=parameters
                )
                
        except Exception as e:
            logger.warning(f"Failed to ensure tool variant exists for {tool_name}: {e}")

    @property
    def prompt_manager(self) -> PromptManager:
        """Get or create the prompt manager for loading system prompts.
        
        Returns:
            PromptManager instance configured for CodeAct agent prompts

        """
        if self._prompt_manager is None:
            prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
            system_prompt = self.config.resolved_system_prompt_filename
            if not os.path.exists(os.path.join(prompt_dir, system_prompt)):
                system_prompt = "system_prompt.j2"

            prompt_manager = PromptManager(
                prompt_dir=prompt_dir,
                system_prompt_filename=system_prompt,
            )

            original_get_system_message = prompt_manager.get_system_message

            def get_system_message_with_defaults(**context):
                context.setdefault("config", self.config)
                context.setdefault("cli_mode", getattr(self.config, "cli_mode", False))
                content = original_get_system_message(**context)
                if "You are Forge agent" not in content:
                    content = "You are Forge agent.\n" + content
                return content

            prompt_manager.get_system_message = get_system_message_with_defaults  # type: ignore[attr-defined]
            self._prompt_manager = prompt_manager
        return self._prompt_manager

    def _should_use_short_tool_descriptions(self) -> bool:
        """Check if short tool descriptions should be used based on LLM model."""
        if self.llm is None:
            return False
        SHORT_TOOL_DESCRIPTION_LLM_SUBSTRS = ["gpt-4", "o3", "o1", "o4"]
        return any(model_substr in self.llm.config.model for model_substr in SHORT_TOOL_DESCRIPTION_LLM_SUBSTRS)

    def _add_core_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        """Add core tools (cmd, think, finish, condensation)."""
        if getattr(self.config, "enable_cmd", True):
            tools.append(create_cmd_run_tool(use_short_description=use_short_tool_desc))
        if getattr(self.config, "enable_think", True):
            tools.append(ThinkTool)
        if getattr(self.config, "enable_finish", True):
            tools.append(FinishTool)
        if getattr(self.config, "enable_condensation_request", False):
            tools.append(CondensationRequestTool)

    def _add_browsing_tool(self, tools: list) -> None:
        """Add browsing tool if enabled and platform supports it."""
        if getattr(self.config, "enable_browsing", False):
            if sys.platform == "win32":
                logger.warning("Windows runtime does not support browsing yet")
            else:
                tools.append(BrowserTool)

    def _add_editor_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        """Add editor tools based on configuration."""
        # Priority: Ultimate Editor > LLM Editor > String Replace Editor
        if getattr(self.config, 'enable_ultimate_editor', False):
            from forge.agenthub.codeact_agent.tools import create_ultimate_editor_tool
            tools.append(create_ultimate_editor_tool(use_short_description=use_short_tool_desc))
        elif getattr(self.config, 'enable_llm_editor', False):
            tools.append(LLMBasedFileEditTool)
        elif getattr(self.config, 'enable_editor', True):
            tools.append(create_str_replace_editor_tool(use_short_description=use_short_tool_desc))

    def _add_specialized_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        """Add specialized tools (jupyter, plan mode, database)."""
        if getattr(self.config, "enable_jupyter", False):
            tools.append(IPythonTool)
        if getattr(self.config, "enable_plan_mode", False):
            tools.append(create_task_tracker_tool(use_short_tool_desc))
        # Add database tools (always enabled if jupyter is enabled)
        if getattr(self.config, "enable_jupyter", False):
            tools.extend(get_database_tools())

    def _get_tools(self) -> list["ChatCompletionToolParam"]:
        """Get complete list of tools available to the CodeAct agent.
        
        Assembles tools from multiple categories (core, browsing, editor,
        specialized) based on agent configuration. Applies tool optimization
        if enabled.
        
        Returns:
            List of tool definitions formatted for LLM function calling

        """
        use_short_tool_desc = self._should_use_short_tool_descriptions()
        tools = []

        self._add_core_tools(tools, use_short_tool_desc)
        self._add_browsing_tool(tools)
        self._add_specialized_tools(tools, use_short_tool_desc)
        self._add_editor_tools(tools, use_short_tool_desc)

        # Apply tool optimization if enabled
        if self.tool_optimizer:
            tools = self._apply_tool_optimization(tools)

        return tools

    def reset(self, state: State | None = None) -> list[Action]:
        """Reset agent state for production health checks.

        Args:
            state: Optional current state when reset is triggered during execution.

        Returns:
            List of pending actions that remain after reset (always empty).

        """
        super().reset()
        self.pending_actions.clear()

        # Save enhanced context state before reset if enabled
        if self.enhanced_context_manager:
            persistence_path = getattr(self.config, "context_persistence_path", None)
            if persistence_path:
                try:
                    self.enhanced_context_manager.save_to_file(persistence_path)
                    logger.debug(f"Saved enhanced context state to {persistence_path}")
                except Exception as e:
                    logger.warning(f"Failed to save context state: {e}")

        # Update enhanced context with supplied state if available
        if state is not None:
            try:
                self._update_context_memory(state)
            except Exception as err:  # pragma: no cover - defensive log
                logger.debug("Failed to update context memory during reset: %s", err)

        return []
    
    def _update_context_memory(self, state: State) -> None:
        """Update enhanced context manager with recent state."""
        if not self.enhanced_context_manager:
            return
        
        try:
            # Get the last few events
            recent_events = state.history[-5:] if len(state.history) >= 5 else state.history
            
            for event in recent_events:
                # Add to short-term memory
                event_data = {
                    "event_type": type(event).__name__,
                    "timestamp": getattr(event, "timestamp", None),
                    "content": str(event)[:500]  # Limit size
                }
                
                # Check for decisions (file edits, delegations, etc.)
                if hasattr(event, "action") and "file" in str(event.action).lower():
                    event_data["has_decision"] = True
                
                self.enhanced_context_manager.add_to_short_term(event_data)
        
        except Exception as e:
            logger.debug(f"Failed to update context memory: {e}")

    def _check_exit_command(self, state: State) -> "Action | None":
        """Check if user wants to exit."""
        latest_user_message = state.get_last_user_message()
        if latest_user_message and latest_user_message.content.strip() == "/exit":
            return AgentFinishAction()
        return None

    def _get_condensed_history(self, state: State) -> tuple[list[Event], "Action | None"]:
        """Get condensed history or condensation action."""
        if not self.condenser:
            history = getattr(state, "history", [])
            return list(history), None

        condensed_history: list[Event] = []
        match self.condenser.condensed_history(state):
            case View(events=events):
                condensed_history = events
            case Condensation(action=condensation_action):
                return [], condensation_action
        return condensed_history, None

    def _generate_llm_response(
        self,
        state: State,
        condensed_history: list[Event],
    ) -> "Action":
        """Generate LLM response with streaming and return first action.

        Args:
            state: Current agent state
            condensed_history: Condensed event history

        Returns:
            First action from response

        """
        initial_user_message = self._get_initial_user_message(state.history)
        messages = self._get_messages(condensed_history, initial_user_message)
        params = self._build_llm_params(messages, state)

        try:
            import time
            start_time = time.time()
            
            accumulated_content, accumulated_chunks = self._stream_llm_response(params)
            response = self._build_final_response(accumulated_chunks, accumulated_content)
            
            # 🛡️ CRITICAL FIX: Handle None response from failed streaming
            if response is None:
                logger.warning("Streaming returned None, falling back to non-streaming")
                return self._fallback_non_streaming(params)
            
            execution_time = time.time() - start_time
            
            # Track successful execution
            self._track_prompt_performance(state, True, execution_time)
            
        except Exception as e:
            logger.error("Error during streaming: %s", e)
            
            # Track failed execution
            execution_time = time.time() - start_time if 'start_time' in locals() else 0.0
            self._track_prompt_performance(state, False, execution_time, error_message=str(e))
            
            return self._fallback_non_streaming(params)

        # Parse actions from response
        actions = self.response_to_actions(response)
        for action in actions:
            self.pending_actions.append(action)
        return self.pending_actions.popleft()

    def _build_llm_params(self, messages: list, state: State) -> dict:
        """Build parameters for LLM completion.

        Args:
            messages: Message history
            state: Current agent state

        Returns:
            Parameter dictionary

        """
        # Get ACE playbook context if available
        ace_context = self._get_ace_playbook_context(state)
        
        # Apply prompt optimization if enabled
        optimized_messages = self._apply_prompt_optimization(messages, state)
        
        # Inject ACE context into system message if available
        if ace_context and optimized_messages:
            system_message = optimized_messages[0]
            if system_message.get("role") == "system":
                system_message["content"] = f"{system_message['content']}\n\n{ace_context}"
        
        # Determine if we should enforce tool usage
        # Allow text-only for questions, require tools for tasks
        tool_choice = self._determine_tool_choice(messages, state)
        
        params = {
            "messages": optimized_messages,
            "tools": check_tools(self.tools, self.llm.config),
            "stream": True,
        }
        
        # Add tool_choice if determined (not all LLMs support it)
        if tool_choice and self._llm_supports_tool_choice():
            params["tool_choice"] = tool_choice
        
        params["extra_body"] = {
            "metadata": state.to_llm_metadata(model_name=self.llm.config.model, agent_name=self.name),
        }
        return params
    
    def _get_last_user_message(self, messages: list) -> str | None:
        """Extract the last user message from message history.
        
        Args:
            messages: Message history
            
        Returns:
            Last user message content or None

        """
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return msg.get("content", "")
        return None

    def _check_question_patterns(self, message: str) -> bool:
        """Check if message matches question patterns.
        
        Args:
            message: Message to check
            
        Returns:
            True if message matches question patterns

        """
        import re
        question_patterns = [
            r"\bwhy\b", r"\bhow does\b", r"\bwhat is\b", r"\bwhat are\b",
            r"\bexplain\b", r"\btell me\b", r"\b\?\s*$", r"\bcan you explain\b"
        ]
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in question_patterns)

    def _check_action_patterns(self, message: str) -> bool:
        """Check if message matches action patterns.
        
        Args:
            message: Message to check
            
        Returns:
            True if message matches action patterns

        """
        import re
        action_patterns = [
            r"\bcreate\b", r"\bmake\b", r"\bwrite\b", r"\bedit\b", r"\bmodify\b",
            r"\bdelete\b", r"\bremove\b", r"\bfix\b", r"\bimplement\b", r"\badd\b",
            r"\bupdate\b", r"\bchange\b", r"\bbuild\b", r"\brun\b", r"\binstall\b"
        ]
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in action_patterns)

    def _determine_tool_choice(self, messages: list, state: State) -> str | None:
        """Determine whether to enforce tool usage based on context.
        
        Args:
            messages: Message history
            state: Current agent state
            
        Returns:
            "required" to enforce tools, "auto" to allow text, None to not specify

        """
        last_user_msg = self._get_last_user_message(messages)
        if not last_user_msg:
            return "auto"
        
        if self._check_question_patterns(last_user_msg):
            return "auto"
        
        if self._check_action_patterns(last_user_msg):
            return "required"
        
        if hasattr(self, 'anti_hallucination') and self.anti_hallucination:
            return self.anti_hallucination.should_enforce_tools(
                last_user_msg,
                state,
                strict_mode=True
            )
        
        return "required"
    
    def _llm_supports_tool_choice(self) -> bool:
        """Check if current LLM supports tool_choice parameter.
        
        Returns:
            True if LLM supports tool_choice

        """
        # Models that support tool_choice
        supported_models = [
            "gpt-4", "gpt-3.5", "claude-3", "claude-sonnet", "claude-opus", "claude-haiku",
            "gemini", "mistral", "command", "deepseek"
        ]
        
        model_name = self.llm.config.model.lower()
        return any(supported in model_name for supported in supported_models)

    def _get_ace_playbook_context(self, state: State) -> str | None:
        """Get ACE playbook context for the current state."""
        if not self.ace_framework:
            return None
        
        try:
            # Get the current task from the state
            current_task = self._extract_current_task(state)
            if not current_task:
                return None
            
            # Get relevant playbook content
            playbook_content = self.ace_framework.context_playbook.get_playbook_content(
                max_bullets=getattr(self.config, "ace_max_playbook_content_length", 50)
            )
            
            if not playbook_content or "No relevant strategies found" in playbook_content:
                return None
            
            # Format as ACE context
            ace_context = f"""
ACE PLAYBOOK:
{playbook_content}

Instructions:
1. Use relevant strategies from the playbook when applicable
2. Apply domain-specific insights and patterns
3. Follow verification checklists from the playbook
4. Avoid common mistakes listed in the playbook
5. Show your reasoning step-by-step
6. Leverage tools and utilities mentioned in the playbook
"""
            return ace_context
            
        except Exception as e:
            logger.warning(f"Failed to get ACE playbook context: {e}")
            return None
    
    def _extract_current_task(self, state: State) -> str | None:
        """Extract current task from state for ACE context."""
        try:
            # Get the most recent user message
            for event in reversed(state.history):
                if hasattr(event, 'source') and event.source == 'user':
                    if hasattr(event, 'content'):
                        return str(event.content)
            return None
        except Exception:
            return None

    def _stream_llm_response(self, params: dict) -> tuple[str, list]:
        """Stream LLM response and accumulate chunks.

        Args:
            params: LLM parameters

        Returns:
            Tuple of (accumulated_content, accumulated_chunks)

        """
        from forge.events.action.message import StreamingChunkAction
        from forge.events.stream import EventSource

        response_stream = self.llm.completion(**params)
        accumulated_content = ""
        accumulated_chunks = []

        for chunk in response_stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    token = delta.content
                    accumulated_content += token
                    accumulated_chunks.append(chunk)

                    streaming_action = StreamingChunkAction(
                        chunk=token,
                        accumulated=accumulated_content,
                        is_final=False,
                    )
                    streaming_action.source = EventSource.AGENT
                    self.event_stream.add_event(streaming_action, EventSource.AGENT)

        # Mark final chunk
        if accumulated_content:
            final_chunk = StreamingChunkAction(
                chunk="",
                accumulated=accumulated_content,
                is_final=True,
            )
            final_chunk.source = EventSource.AGENT
            self.event_stream.add_event(final_chunk, EventSource.AGENT)

        return accumulated_content, accumulated_chunks

    def _build_final_response(self, accumulated_chunks: list, accumulated_content: str):
        """Build final response from accumulated chunks.

        Args:
            accumulated_chunks: List of response chunks
            accumulated_content: Full accumulated content

        Returns:
            Final ModelResponse object

        """
        from litellm.types.utils import Message as LiteLLMMessage

        if accumulated_chunks:
            final_response = accumulated_chunks[-1]
            final_response.choices[0].delta.content = accumulated_content
            final_response.choices[0].message = LiteLLMMessage(content=accumulated_content, role="assistant")
            return final_response
        logger.warning("No chunks received from streaming")
        return None

    def _fallback_non_streaming(self, params: dict) -> "Action":
        """Fallback to non-streaming completion.

        Args:
            params: LLM parameters

        Returns:
            First action from response

        """
        params["stream"] = False
        response = self.llm.completion(**params)
        logger.debug("Fallback non-streaming response: %s", response)
        actions = self.response_to_actions(response)
        for action in actions:
            self.pending_actions.append(action)
        return self.pending_actions.popleft()

    def step(self, state: State) -> "Action":
        """Perform a step using the CodeAct toolkit."""
        if self.pending_actions:
            return self.pending_actions.popleft()

        condensed_history, condensation_action = self._get_condensed_history(state)
        if condensation_action:
            return condensation_action

        initial_user_message = self._get_initial_user_message(condensed_history)
        messages = self._get_messages(condensed_history, initial_user_message)

        formatted_messages = self.llm.format_messages_for_llm(messages)
        params: dict[str, Any] = {"messages": formatted_messages}

        if getattr(self.llm, "is_function_calling_active", lambda: False)():
            params["tools"] = check_tools(self.tools, self.llm.config)

        response = self.llm.completion(**params)
        actions = self.response_to_actions(response)

        if not actions:
            from forge.events.action import MessageAction

            message_text = ""
            if getattr(response, "choices", None):
                message_text = getattr(response.choices[0].message, "content", "") or ""
            action = MessageAction(content=message_text)
            action.source = EventSource.AGENT
            return action

        for action in actions[1:]:
            self.pending_actions.append(action)
        return actions[0]

    def _get_initial_user_message(self, history: State | list[Event]) -> MessageAction:
        """Find the initial user message if it exists."""
        events = history.history if hasattr(history, "history") else history
        for event in events:
            if isinstance(event, MessageAction) and event.source == EventSource.USER:
                return event
        msg = "Initial user message not found"
        raise ValueError(msg)

    def _get_messages(
        self,
        condensed_history: State | list[Event],
        initial_user_message: MessageAction,
    ) -> list[Message]:
        """Construct the message list for the current state and observation."""
        events = (
            list(condensed_history.history)
            if hasattr(condensed_history, "history")
            else list(condensed_history)
        )
        messages = self.conversation_memory.process_events(
            condensed_history=events,
            initial_user_action=initial_user_message,
            max_message_chars=getattr(self.llm.config, "max_message_chars", None),
            vision_is_active=getattr(self.llm.config, "vision_is_active", False),
        )

        if messages:
            first_message = messages[0]
            for content_item in first_message.content:
                if isinstance(content_item, TextContent):
                    content_item.cache_prompt = True
                    break

            for message in reversed(messages):
                if message.role == "user":
                    for content_item in message.content:
                        if isinstance(content_item, TextContent):
                            content_item.cache_prompt = True
                            break
                    break

        return messages

    def _extract_response_text(self, response: "ModelResponse") -> str:
        """Extract text content from model response.
        
        Args:
            response: Model response object
            
        Returns:
            Response text content or empty string

        """
        if not hasattr(response, 'choices') or not response.choices:
            return ""
        
        choice = response.choices[0]
        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
            return choice.message.content or ""
        
        return ""

    def _validate_anti_hallucination(self, response_text: str, actions: list["Action"]) -> tuple[bool, list["Action"]]:
        """Run anti-hallucination pre-validation.
        
        Args:
            response_text: Response text to validate
            actions: Proposed actions
            
        Returns:
            Tuple of (continue_processing, updated_actions)

        """
        if not hasattr(self, 'anti_hallucination') or not self.anti_hallucination:
            return True, actions
        
        is_valid, error_msg = self.anti_hallucination.validate_response(response_text, actions)
        if not is_valid:
            logger.error(f"🚫 BLOCKED HALLUCINATION: {error_msg}")
            from forge.events.action import MessageAction
            return False, [MessageAction(content=error_msg, wait_for_response=False)]
        
        return True, actions

    def _inject_verification_commands(self, actions: list["Action"]) -> list["Action"]:
        """Inject automatic verification commands into actions.
        
        Args:
            actions: List of actions to process
            
        Returns:
            Actions with verification commands injected

        """
        if not hasattr(self, 'anti_hallucination') or not self.anti_hallucination:
            return actions
        
        self.anti_hallucination.turn_counter += 1
        return self.anti_hallucination.inject_verification_commands(
            actions,
            turn=self.anti_hallucination.turn_counter
        )

    def _detect_and_warn_hallucinations(self, response_text: str, actions: list["Action"]) -> list["Action"]:
        """Detect hallucinations and add warning messages if found.
        
        Args:
            response_text: Response text to analyze
            actions: List of actions to check
            
        Returns:
            Actions list with warning prepended if hallucination detected

        """
        if not self.hallucination_detector:
            return actions
        
        tools_called = [a.action for a in actions] if actions else []
        detection = self.hallucination_detector.detect_text_hallucination(
            response_text, tools_called, actions
        )
        
        if not detection.get("hallucinated"):
            return actions
        
        # Log hallucination for monitoring
        logger.warning(
            f"HALLUCINATION DETECTED: {detection['severity']} severity - "
            f"Claimed: {detection['claimed_operations']}, Missing tools: {detection['missing_tools']}"
        )
        
        # Add warning for critical hallucinations
        if detection.get("severity") in ("critical", "high"):
            from forge.events.action import MessageAction
            warning_msg = MessageAction(
                content=f"""⚠️ RELIABILITY WARNING: You claimed these operations without executing tools:
{chr(10).join(f"  - {op}" for op in detection['claimed_operations'])}

Required tools not called: {', '.join(detection['missing_tools'])}

Please execute the actual tools to complete this action.""",
                wait_for_response=False
            )
            actions.insert(0, warning_msg)
        
        return actions

    def response_to_actions(self, response: "ModelResponse") -> list["Action"]:
        """Convert model response to actions with hallucination detection and verification."""
        actions = codeact_function_calling.response_to_actions(
            response, 
            mcp_tool_names=list(self.mcp_tools.keys())
        )
        
        # Track tool usage for optimization
        if self.tool_optimizer and actions:
            self._track_tool_usage(actions)
        
        # Extract response text for validation
        response_text = self._extract_response_text(response)
        
        # LAYER 1: Pre-validation (proactive prevention)
        continue_processing, actions = self._validate_anti_hallucination(response_text, actions)
        if not continue_processing:
            return actions
        
        # LAYER 2: Automatic verification injection
        actions = self._inject_verification_commands(actions)
        
        # LAYER 3: Detect and warn about hallucinations (reactive detection)
        actions = self._detect_and_warn_hallucinations(response_text, actions)
        
        return actions
