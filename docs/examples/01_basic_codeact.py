"""
Basic CodeAct Agent Example

This example shows how to create and use a CodeAct agent programmatically.
"""

import asyncio
from openhands.controller.agent_controller import AgentController
from openhands.core.config import OpenHandsConfig, LLMConfig
from openhands.events.action import MessageAction
from openhands.events.observation import AgentStateChangeObservation
from openhands.core.schema.agent_state import AgentState


async def main():
    """Run a simple CodeAct agent conversation."""
    
    # Configure LLM
    llm_config = LLMConfig(
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-your-key-here",  # Replace with your API key
        temperature=0.0,
        max_output_tokens=8000,
    )
    
    # Create OpenHands config
    config = OpenHandsConfig(
        llm=llm_config,
        agent_name="CodeActAgent",
        workspace_base="./workspace",  # Working directory
        max_iterations=30,
    )
    
    # Create agent controller
    controller = AgentController(
        agent_name="CodeActAgent",
        llm=llm_config,
        max_iterations=30,
        event_stream=None,  # Will create default
        sid="example-session"
    )
    
    # Initialize agent
    await controller.setup_task(
        task="Create a Python function that calculates fibonacci numbers recursively. "
             "Add type hints and docstrings."
    )
    
    # Start agent
    print("Starting agent...")
    await controller.set_agent_state_to(AgentState.RUNNING)
    
    # Run agent loop
    while controller.state.agent_state == AgentState.RUNNING:
        # Agent takes one step
        await controller.step()
        
        # Print agent actions
        last_event = controller.state.history[-1] if controller.state.history else None
        if last_event:
            print(f"Event: {last_event.__class__.__name__}")
            if hasattr(last_event, 'content'):
                print(f"Content: {last_event.content[:100]}...")
    
    # Print final state
    print(f"\nAgent finished with state: {controller.state.agent_state}")
    print(f"Total iterations: {controller.state.iteration}")
    
    # Get metrics
    print(f"\nMetrics:")
    print(f"Total cost: ${controller.agent.llm.metrics.accumulated_cost:.2f}")
    print(f"Total tokens: {controller.agent.llm.metrics.total_tokens}")


if __name__ == "__main__":
    asyncio.run(main())

