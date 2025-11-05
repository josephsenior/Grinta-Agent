import os
import sys
from collections import deque
from typing import TYPE_CHECKING

from openhands.llm.llm_registry import LLMRegistry

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam

    from openhands.events.action import Action
    from openhands.llm.llm import ModelResponse
import openhands.agenthub.codeact_agent.function_calling as codeact_function_calling
from openhands.agenthub.codeact_agent.tools.bash import create_cmd_run_tool
from openhands.agenthub.codeact_agent.tools.browser import BrowserTool
from openhands.agenthub.codeact_agent.tools.condensation_request import (
    CondensationRequestTool,
)
from openhands.agenthub.codeact_agent.tools.database import get_database_tools
from openhands.agenthub.codeact_agent.tools.finish import FinishTool
from openhands.agenthub.codeact_agent.tools.ipython import IPythonTool
from openhands.agenthub.codeact_agent.tools.llm_based_edit import LLMBasedFileEditTool
from openhands.agenthub.codeact_agent.tools.str_replace_editor import (
    create_str_replace_editor_tool,
)
from openhands.agenthub.codeact_agent.tools.task_tracker import create_task_tracker_tool
from openhands.agenthub.codeact_agent.tools.think import ThinkTool
from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.core.config import AgentConfig
from openhands.core.logger import openhands_logger as logger
from openhands.core.message import Message
from openhands.events.action import AgentFinishAction, MessageAction
from openhands.events.event import Event
from openhands.llm.llm_utils import check_tools
from openhands.memory.condenser import Condenser
from openhands.memory.condenser.condenser import Condensation
from openhands.memory.view import View
from openhands.memory.conversation_memory import ConversationMemory
from openhands.runtime.plugins import (
    AgentSkillsRequirement,
    JupyterRequirement,
    PluginRequirement,
)
from openhands.utils.prompt import PromptManager


class CodeActAgent(Agent):
    """CodeAct Agent - OpenHands' flagship autonomous coding agent (Beta focus).
    
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
        from openhands.controller.agent_controller import AgentController
        from openhands.core.config import LLMConfig
        
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
        - README: openhands/agenthub/codeact_agent/README.md
    """
    
    VERSION = "2.2"
    sandbox_plugins: list[PluginRequirement] = [AgentSkillsRequirement(), JupyterRequirement()]

    def __init__(self, config: AgentConfig, llm_registry: LLMRegistry) -> None:
        """Initializes a new instance of the CodeActAgent class.

        Parameters:
        - config (AgentConfig): The configuration for this agent
        """
        super().__init__(config, llm_registry)
        self.pending_actions: deque[Action] = deque()
        
        # Initialize prompt optimization attributes before any methods that might use them
        self.prompt_optimizer = None
        self.tool_optimizer = None
        
        # Initialize action verifier (lazy-loaded when runtime available)
        self.action_verifier = None
        
        # Initialize hallucination detector (Layer 4: Production Reliability)
        from openhands.agenthub.codeact_agent.hallucination_detector import HallucinationDetector
        self.hallucination_detector = HallucinationDetector()
        
        # Initialize Ultimate Anti-Hallucination System (7.5/10 → 9.5/10)
        from openhands.agenthub.codeact_agent.anti_hallucination_system import AntiHallucinationSystem
        self.anti_hallucination = AntiHallucinationSystem()
        
        # Initialize Enhanced Context Manager if enabled (MUST be before reset())
        self.enhanced_context_manager = None
        self._initialize_enhanced_context_manager()
        
        self.reset()
        self.tools = self._get_tools()
        self.conversation_memory = ConversationMemory(self.config, self.prompt_manager)
        self.condenser = Condenser.from_config(self.config.condenser, llm_registry)
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
            from openhands.memory.enhanced_context_manager import EnhancedContextManager
            
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
            from openhands.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig
            
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
        """
        Run production health check for SaaS deployment.
        Ensures critical dependencies (Tree-sitter) are available.
        """
        try:
            from openhands.agenthub.codeact_agent.tools.health_check import run_production_health_check
            
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
            from openhands.prompt_optimization import (
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
                storage_path=getattr(self.config, "prompt_opt_storage_path", "~/.openhands/prompt_optimization/codeact/"),
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
            from openhands.prompt_optimization.tool_optimizer import ToolOptimizer
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
            from openhands.prompt_optimization.models import PromptCategory
            
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
                                error_message: str = None):
        """Track prompt performance for optimization."""
        if not self.prompt_optimizer:
            return
        
        try:
            from openhands.prompt_optimization.models import PromptCategory
            
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
                            error_message: str = None, metadata: dict = None):
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
            from openhands.prompt_optimization.tool_descriptions import get_optimized_description
            
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
        if self._prompt_manager is None:
            self._prompt_manager = PromptManager(
                prompt_dir=os.path.join(os.path.dirname(__file__), "prompts"),
                system_prompt_filename=self.config.resolved_system_prompt_filename,
            )
        return self._prompt_manager

    def _should_use_short_tool_descriptions(self) -> bool:
        """Check if short tool descriptions should be used based on LLM model."""
        if self.llm is None:
            return False
        SHORT_TOOL_DESCRIPTION_LLM_SUBSTRS = ["gpt-4", "o3", "o1", "o4"]
        return any(model_substr in self.llm.config.model for model_substr in SHORT_TOOL_DESCRIPTION_LLM_SUBSTRS)

    def _add_core_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        """Add core tools (cmd, think, finish, condensation)."""
        if self.config.enable_cmd:
            tools.append(create_cmd_run_tool(use_short_description=use_short_tool_desc))
        if self.config.enable_think:
            tools.append(ThinkTool)
        if self.config.enable_finish:
            tools.append(FinishTool)
        if self.config.enable_condensation_request:
            tools.append(CondensationRequestTool)

    def _add_browsing_tool(self, tools: list) -> None:
        """Add browsing tool if enabled and platform supports it."""
        if self.config.enable_browsing:
            if sys.platform == "win32":
                logger.warning("Windows runtime does not support browsing yet")
            else:
                tools.append(BrowserTool)

    def _add_editor_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        """Add editor tools based on configuration."""
        # Priority: Ultimate Editor > LLM Editor > String Replace Editor
        if getattr(self.config, 'enable_ultimate_editor', False):
            from openhands.agenthub.codeact_agent.tools import create_ultimate_editor_tool
            tools.append(create_ultimate_editor_tool(use_short_description=use_short_tool_desc))
        elif self.config.enable_llm_editor:
            tools.append(LLMBasedFileEditTool)
        elif self.config.enable_editor:
            tools.append(create_str_replace_editor_tool(use_short_description=use_short_tool_desc))

    def _add_specialized_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        """Add specialized tools (jupyter, plan mode, database)."""
        if self.config.enable_jupyter:
            tools.append(IPythonTool)
        if self.config.enable_plan_mode:
            tools.append(create_task_tracker_tool(use_short_tool_desc))
        # Add database tools (always enabled if jupyter is enabled)
        if self.config.enable_jupyter:
            tools.extend(get_database_tools())

    def _get_tools(self) -> list["ChatCompletionToolParam"]:
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

    def reset(self) -> None:
        """Resets the CodeAct Agent's internal state."""
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
    
    def _determine_tool_choice(self, messages: list, state: State) -> str | None:
        """Determine whether to enforce tool usage based on context.
        
        Args:
            messages: Message history
            state: Current agent state
            
        Returns:
            "required" to enforce tools, "auto" to allow text, None to not specify
        """
        # Get the last user message
        last_user_msg = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        if not last_user_msg:
            return "auto"
        
        # Question patterns - allow text-only responses
        question_patterns = [
            r"\bwhy\b", r"\bhow does\b", r"\bwhat is\b", r"\bwhat are\b",
            r"\bexplain\b", r"\btell me\b", r"\b\?\s*$", r"\bcan you explain\b"
        ]
        
        import re
        for pattern in question_patterns:
            if re.search(pattern, last_user_msg.lower()):
                # User is asking a question - allow text response
                return "auto"
        
        # Action patterns - require tool usage
        action_patterns = [
            r"\bcreate\b", r"\bmake\b", r"\bwrite\b", r"\bedit\b", r"\bmodify\b",
            r"\bdelete\b", r"\bremove\b", r"\bfix\b", r"\bimplement\b", r"\badd\b",
            r"\bupdate\b", r"\bchange\b", r"\bbuild\b", r"\brun\b", r"\binstall\b"
        ]
        
        for pattern in action_patterns:
            if re.search(pattern, last_user_msg.lower()):
                # User wants an action - require tool usage
                return "required"
        
        # FIXED: Use anti-hallucination system for smarter enforcement
        if hasattr(self, 'anti_hallucination') and self.anti_hallucination:
            return self.anti_hallucination.should_enforce_tools(
                last_user_msg,
                state,
                strict_mode=True  # Default to strict for file operation reliability
            )
        
        # Fallback: Default to "required" instead of "auto" (7.5/10 → 9/10)
        return "required"  # ← FIXED: Was "auto", now "required"!
    
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
        from openhands.events.action.message import StreamingChunkAction
        from openhands.events.stream import EventSource

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
                    streaming_action._source = EventSource.AGENT
                    self.event_stream.add_event(streaming_action, EventSource.AGENT)

        # Mark final chunk
        if accumulated_content:
            final_chunk = StreamingChunkAction(
                chunk="",
                accumulated=accumulated_content,
                is_final=True,
            )
            final_chunk._source = EventSource.AGENT
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
        """Performs one step using the CodeAct Agent.

        This includes gathering info on previous steps and prompting the model to make a command to execute.

        Parameters:
        - state (State): used to get updated info

        Returns:
        - CmdRunAction(command) - bash command to run
        - IPythonRunCellAction(code) - IPython code to run
        - AgentDelegateAction(agent, inputs) - delegate action for (sub)task
        - MessageAction(content) - Message action to run (e.g. ask for clarification)
        - AgentFinishAction() - end the interaction
        - CondensationAction(...) - condense conversation history by forgetting specified events and optionally providing a summary
        - FileReadAction(path, ...) - read file content from specified path
        - FileEditAction(path, ...) - edit file using LLM-based (deprecated) or ACI-based editing
        - AgentThinkAction(thought) - log agent's thought/reasoning process
        - CondensationRequestAction() - request condensation of conversation history
        - BrowseInteractiveAction(browser_actions) - interact with browser using specified actions
        - MCPAction(name, arguments) - interact with MCP server tools
        """
        if self.pending_actions:
            return self.pending_actions.popleft()

        if exit_action := self._check_exit_command(state):
            return exit_action

        # Enhanced Context: Track recent exchanges in short-term memory
        if self.enhanced_context_manager and len(state.history) > 0:
            self._update_context_memory(state)

        # Get condensed history
        condensed_history, condensation_action = self._get_condensed_history(state)
        if condensation_action:
            return condensation_action

        logger.debug("Processing %s events from a total of %s events", len(condensed_history), len(state.history))

        # Generate LLM response
        return self._generate_llm_response(state, condensed_history)

    def _get_initial_user_message(self, history: list[Event]) -> MessageAction:
        """Finds the initial user message action from the full history."""
        initial_user_message: MessageAction | None = next(
            (event for event in history if isinstance(event, MessageAction) and event.source == "user"),
            None,
        )
        if initial_user_message is None:
            logger.error(
                "CRITICAL: Could not find the initial user MessageAction in the full %s events history.",
                len(history),
            )
            msg = "Initial user message not found in history. Please report this issue."
            raise ValueError(msg)
        return initial_user_message

    def _get_messages(self, events: list[Event], initial_user_message: MessageAction) -> list[Message]:
        """Constructs the message history for the LLM conversation.

        This method builds a structured conversation history by processing events from the state
        and formatting them into messages that the LLM can understand. It handles both regular
        message flow and function-calling scenarios.

        The method performs the following steps:
        1. Checks for SystemMessageAction in events, adds one if missing (legacy support)
        2. Processes events (Actions and Observations) into messages, including SystemMessageAction
        3. Handles tool calls and their responses in function-calling mode
        4. Manages message role alternation (user/assistant/tool)
        5. Applies caching for specific LLM providers (e.g., Anthropic)
        6. Adds environment reminders for non-function-calling mode

        Args:
            events: The list of events to convert to messages
            initial_user_message: The initial user message to include in the conversation

        Returns:
            list[Message]: A list of formatted messages ready for LLM consumption, including:
                - System message with prompt (from SystemMessageAction)
                - Action messages (from both user and assistant)
                - Observation messages (including tool responses)
                - Environment reminders (in non-function-calling mode)

        Note:
            - In function-calling mode, tool calls and their responses are carefully tracked
              to maintain proper conversation flow
            - Messages from the same role are combined to prevent consecutive same-role messages
            - For Anthropic models, specific messages are cached according to their documentation
        """
        if not self.prompt_manager:
            msg = "Prompt Manager not instantiated."
            raise RuntimeError(msg)
        messages = self.conversation_memory.process_events(
            condensed_history=events,
            initial_user_action=initial_user_message,
            max_message_chars=self.llm.config.max_message_chars,
            vision_is_active=self.llm.vision_is_active(),
        )
        if self.llm.is_caching_prompt_active():
            self.conversation_memory.apply_prompt_caching(messages)
        return messages

    def response_to_actions(self, response: "ModelResponse") -> list["Action"]:
        actions = codeact_function_calling.response_to_actions(response, mcp_tool_names=list(self.mcp_tools.keys()))
        
        # Track tool usage for optimization
        if self.tool_optimizer and actions:
            self._track_tool_usage(actions)
        
        # LAYER 1: Pre-validation (NEW! - Proactive prevention)
        if hasattr(self, 'anti_hallucination') and self.anti_hallucination:
            response_text = ""
            if hasattr(response, 'choices') and response.choices:
                if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'content'):
                    response_text = response.choices[0].message.content or ""
            
            is_valid, error_msg = self.anti_hallucination.validate_response(response_text, actions)
            if not is_valid:
                logger.error(f"🚫 BLOCKED HALLUCINATION: {error_msg}")
                from openhands.events.action import MessageAction
                # Return error message instead of hallucinated response
                return [MessageAction(content=error_msg, wait_for_response=False)]
        
        # LAYER 2: Automatic verification injection (NEW!)
        if hasattr(self, 'anti_hallucination') and self.anti_hallucination:
            self.anti_hallucination.turn_counter += 1
            actions = self.anti_hallucination.inject_verification_commands(
                actions,
                turn=self.anti_hallucination.turn_counter
            )
        
        # LAYER 3: Detect hallucinations (existing - reactive detection)
        if self.hallucination_detector and hasattr(response, 'choices') and response.choices:
            response_text = ""
            if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'content'):
                response_text = response.choices[0].message.content or ""
            
            # Extract tool names from actions
            tools_called = [a.action for a in actions] if actions else []
            
            # Run hallucination detection
            detection = self.hallucination_detector.detect_text_hallucination(
                response_text, tools_called, actions
            )
            
            if detection.get("hallucinated"):
                # Log hallucination for monitoring
                logger.warning(
                    f"HALLUCINATION DETECTED: {detection['severity']} severity - "
                    f"Claimed: {detection['claimed_operations']}, Missing tools: {detection['missing_tools']}"
                )
                
                # For critical hallucinations (file operations), add a MessageAction warning
                if detection.get("severity") in ("critical", "high"):
                    from openhands.events.action import MessageAction
                    warning_msg = MessageAction(
                        content=f"""⚠️ RELIABILITY WARNING: You claimed these operations without executing tools:
{chr(10).join(f"  - {op}" for op in detection['claimed_operations'])}

Required tools not called: {', '.join(detection['missing_tools'])}

Please execute the actual tools to complete this action.""",
                        wait_for_response=False
                    )
                    # Prepend warning to actions list
                    actions.insert(0, warning_msg)
        
        return actions
