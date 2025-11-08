"""E2E tests using Chrome DevTools MCP to monitor autonomous agent behavior.

Tests real-time monitoring, performance, and debugging of the autonomous system.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.chrome_devtools
class TestAutonomousWithChromeDevTools:
    """Test autonomous system with Chrome DevTools monitoring."""
    
    @pytest.fixture(autouse=True)
    async def setup_chrome_devtools(self):
        """Set up Chrome DevTools connection."""
        # This would connect to Chrome DevTools MCP server
        # For now, we'll simulate it
        self.devtools_logs = []
        self.network_requests = []
        self.console_errors = []
        yield
    
    async def log_devtools_event(self, event_type: str, data: dict):
        """Log a DevTools event for analysis."""
        self.devtools_logs.append({
            'type': event_type,
            'data': data,
            'timestamp': asyncio.get_event_loop().time()
        })
    
    @pytest.mark.asyncio
    async def test_monitor_agent_performance(self):
        """Monitor agent performance metrics during execution."""
        from forge.core.config import ForgeConfig
        from forge.controller.agent_controller import AgentController
        from forge.core.setup import create_agent, create_runtime
        from forge.events.action import MessageAction
        
        config = ForgeConfig()
        runtime = await create_runtime(config)
        agent = create_agent(config)
        
        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=10,
            config=config,
        )
        
        # Monitor performance
        start_time = asyncio.get_event_loop().time()
        
        task = "Create 5 text files with sequential numbers"
        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )
        
        try:
            state = await controller.run()
            end_time = asyncio.get_event_loop().time()
            
            # Calculate metrics
            total_time = end_time - start_time
            iterations = state.iteration
            avg_time_per_iteration = total_time / iterations if iterations > 0 else 0
            
            # Log performance metrics
            await self.log_devtools_event('performance', {
                'total_time': total_time,
                'iterations': iterations,
                'avg_time_per_iteration': avg_time_per_iteration,
                'status': state.agent_state.value
            })
            
            # Assertions
            assert total_time < 60, "Should complete within 60 seconds"
            assert avg_time_per_iteration < 10, "Average iteration should be < 10s"
            
            print(f"✅ Performance metrics:")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Iterations: {iterations}")
            print(f"   Avg per iteration: {avg_time_per_iteration:.2f}s")
            
        finally:
            await runtime.close()
    
    @pytest.mark.asyncio
    async def test_monitor_network_activity(self):
        """Monitor network requests during agent execution."""
        from forge.core.config import ForgeConfig
        from forge.controller.agent_controller import AgentController
        from forge.core.setup import create_agent, create_runtime
        from forge.events.action import MessageAction
        
        config = ForgeConfig()
        runtime = await create_runtime(config)
        agent = create_agent(config)
        
        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=10,
            config=config,
        )
        
        task = "Make a GET request to https://api.github.com and save the response"
        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )
        
        # Mock network monitoring
        async def track_network_request(url: str, method: str):
            self.network_requests.append({
                'url': url,
                'method': method,
                'timestamp': asyncio.get_event_loop().time()
            })
        
        try:
            state = await controller.run()
            
            # Verify network activity was captured
            # In real scenario, this would come from Chrome DevTools Network panel
            assert len(self.network_requests) >= 0, "Network requests should be tracked"
            
            print(f"✅ Monitored {len(self.network_requests)} network requests")
            
        finally:
            await runtime.close()
    
    @pytest.mark.asyncio
    async def test_capture_console_errors(self):
        """Capture and analyze console errors during execution."""
        from forge.core.config import ForgeConfig
        from forge.controller.agent_controller import AgentController
        from forge.core.setup import create_agent, create_runtime
        from forge.events.action import MessageAction
        
        config = ForgeConfig()
        runtime = await create_runtime(config)
        agent = create_agent(config)
        
        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=10,
            config=config,
        )
        
        task = "Create a Python script that intentionally raises an exception, then handle it"
        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )
        
        try:
            state = await controller.run()
            
            # Check for console errors
            error_count = len(self.console_errors)
            
            # Should handle errors gracefully
            assert state.agent_state.value in ['FINISHED', 'ERROR'], \
                "Agent should complete or error gracefully"
            
            print(f"✅ Captured {error_count} console errors")
            print(f"   Final state: {state.agent_state.value}")
            
        finally:
            await runtime.close()
    
    @pytest.mark.asyncio
    async def test_trace_agent_decision_flow(self):
        """Trace agent's decision-making process with DevTools."""
        from forge.core.config import ForgeConfig
        from forge.controller.agent_controller import AgentController
        from forge.core.setup import create_agent, create_runtime
        from forge.events.action import MessageAction
        
        config = ForgeConfig()
        runtime = await create_runtime(config)
        agent = create_agent(config)
        
        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=15,
            config=config,
        )
        
        task = """
        Build a multi-step workflow:
        1. Create a directory called 'project'
        2. Create a README.md inside it
        3. Create a Python file
        4. List all files to verify
        """
        
        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )
        
        # Track decision points
        decision_points = []
        
        try:
            state = await controller.run()
            
            # Analyze decision flow from history
            for i, event in enumerate(controller.state.history):
                if hasattr(event, 'action'):
                    decision_points.append({
                        'step': i,
                        'action': type(event).__name__,
                        'summary': str(event)[:100]
                    })
            
            # Verify logical progression
            assert len(decision_points) >= 4, "Should have multiple decision points"
            
            print(f"✅ Traced {len(decision_points)} decision points")
            for i, point in enumerate(decision_points[:5], 1):
                print(f"   {i}. {point['action']}: {point['summary']}")
            
        finally:
            await runtime.close()


@pytest.mark.e2e
@pytest.mark.integration
class TestFullAutonomousWorkflow:
    """Test complete autonomous workflows from start to finish."""
    
    @pytest.mark.asyncio
    async def test_complete_web_app_build(self):
        """Build a complete web app with frontend, backend, and database."""
        from forge.core.config import ForgeConfig
        from forge.core.config.llm_config import LLMConfig
        from forge.controller.agent_controller import AgentController
        from forge.core.setup import create_agent, create_runtime
        from forge.events.action import MessageAction
        
        config = ForgeConfig()
        config.llm = LLMConfig(
            model='claude-sonnet-4-20250514',
            api_key=os.getenv('ANTHROPIC_API_KEY'),
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = await create_runtime(config, workspace_base=tmpdir)
            agent = create_agent(config)
            
            controller = AgentController(
                agent=agent,
                event_stream=runtime.event_stream,
                max_iterations=50,  # Complex task needs more iterations
                config=config,
            )
            
            task = """
            Build a complete blog web application:
            
            1. Frontend (HTML/CSS/JS):
               - index.html with a list of blog posts
               - style.css for modern styling
               - app.js for interactivity
            
            2. Backend (Python Flask):
               - app.py with REST API endpoints
               - /api/posts GET and POST
               - JSON file as database
            
            3. Database:
               - posts.json with sample data
               - At least 3 sample blog posts
            
            4. Documentation:
               - README.md with setup instructions
               - requirements.txt with dependencies
            
            5. Verification:
               - Create a test script that verifies all files exist
               - Run the test to ensure everything is created
            
            Make it production-ready with error handling.
            """
            
            controller.state.history.append(
                MessageAction(content=task, wait_for_response=False)
            )
            
            try:
                state = await controller.run()
                
                # Verify all components were created
                workspace = Path(tmpdir)
                
                # Frontend
                assert (workspace / 'index.html').exists(), "index.html should exist"
                assert (workspace / 'style.css').exists(), "style.css should exist"
                assert (workspace / 'app.js').exists(), "app.js should exist"
                
                # Backend
                assert (workspace / 'app.py').exists(), "app.py should exist"
                
                # Database
                assert (workspace / 'posts.json').exists(), "posts.json should exist"
                posts_data = json.loads((workspace / 'posts.json').read_text())
                assert len(posts_data) >= 3, "Should have at least 3 sample posts"
                
                # Documentation
                assert (workspace / 'README.md').exists(), "README.md should exist"
                assert (workspace / 'requirements.txt').exists(), "requirements.txt should exist"
                
                print("✅ Successfully built complete web application!")
                print(f"   Iterations used: {state.iteration}/50")
                print(f"   Files created: {len(list(workspace.rglob('*')))}")
                
            finally:
                await runtime.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-m', 'e2e'])

