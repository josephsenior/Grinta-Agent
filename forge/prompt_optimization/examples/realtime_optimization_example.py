"""Real-Time Optimization Example.

Demonstrates how to use the complete real-time optimization system
with live monitoring, WebSocket communication, and instant adaptation.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

from forge.prompt_optimization import (
    PromptOptimizer,
    PromptRegistry,
    PerformanceTracker,
    PromptStorage,
    AdvancedStrategyManager,
    RealTimeOptimizationSystem
)
from forge.prompt_optimization.models import PromptVariant, PromptMetrics, PromptCategory


async def main():
    """Main example demonstrating real-time optimization."""
    print("🚀 Real-Time Optimization System Example")
    print("=" * 50)
    
    # Initialize components
    print("📦 Initializing components...")
    
    # Create base components
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    storage = PromptStorage("./realtime_optimization_data")
    
    # Create base optimizer
    base_optimizer = PromptOptimizer(
        registry=registry,
        tracker=tracker,
        storage=storage
    )
    
    # Create advanced strategy manager
    strategy_manager = AdvancedStrategyManager()
    
    # Create real-time optimization system
    config = {
        'max_concurrent_optimizations': 3,
        'optimization_threshold': 0.05,
        'confidence_threshold': 0.8,
        'max_concurrent_swaps': 2,
        'default_swap_strategy': 'atomic',
        'prediction_model': 'ensemble',
        'retrain_frequency': 50,
        'max_queue_size': 5000,
        'processing_batch_size': 50,
        'processing_interval': 0.1,
        'anomaly_threshold': 2.0,
        'pattern_window_size': 50,
        'monitor_update_interval': 1.0,
        'max_history_size': 5000,
        'trend_window_size': 50,
        'websocket': {
            'host': 'localhost',
            'port': 8765,
            'heartbeat_interval': 30.0,
            'max_clients': 50
        },
        'alert_thresholds': {
            'success_rate': {'warning': 0.7, 'error': 0.5, 'critical': 0.3},
            'execution_time': {'warning': 10.0, 'error': 30.0, 'critical': 60.0},
            'error_rate': {'warning': 0.1, 'error': 0.2, 'critical': 0.4},
            'composite_score': {'warning': 0.6, 'error': 0.4, 'critical': 0.2}
        }
    }
    
    rt_system = RealTimeOptimizationSystem(
        strategy_manager=strategy_manager,
        base_optimizer=base_optimizer,
        config=config
    )
    
    # Initialize the system
    await rt_system.initialize()
    
    print("✅ Components initialized successfully!")
    
    # Start the system
    print("🚀 Starting real-time optimization system...")
    await rt_system.start()
    
    print("✅ Real-time optimization system started!")
    print(f"🌐 WebSocket server running on ws://localhost:8765")
    print(f"📊 Dashboard available at http://localhost:8765/dashboard")
    
    # Create some test prompts
    print("\n📝 Creating test prompts...")
    
    test_prompts = [
        {
            'id': 'system_prompt_1',
            'content': 'You are a helpful AI assistant. Please provide clear and concise responses.',
            'category': PromptCategory.SYSTEM_PROMPT
        },
        {
            'id': 'code_generation_prompt',
            'content': 'Generate clean, efficient code that follows best practices and is well-documented.',
            'category': PromptCategory.TOOL_PROMPT
        },
        {
            'id': 'debugging_prompt',
            'content': 'Debug the following code by identifying issues and providing solutions.',
            'category': PromptCategory.TOOL_PROMPT
        }
    ]
    
    for prompt_data in test_prompts:
        # Create initial variant
        variant = PromptVariant(
            id=f"{prompt_data['id']}_v1",
            prompt_id=prompt_data['id'],
            content=prompt_data['content'],
            category=prompt_data['category'],
            version=1,
            is_active=True
        )
        
        registry.add_variant(variant)
        
        # Create some alternative variants
        for i in range(2, 5):
            alt_variant = PromptVariant(
                id=f"{prompt_data['id']}_v{i}",
                prompt_id=prompt_data['id'],
                content=f"{prompt_data['content']} [Variant {i}]",
                category=prompt_data['category'],
                version=i,
                is_active=False
            )
            registry.add_variant(alt_variant)
        
        print(f"  ✅ Created prompt: {prompt_data['id']} with 4 variants")
    
    # Simulate real-time usage
    print("\n🔄 Simulating real-time usage...")
    
    async def simulate_usage():
        """Simulate real-time prompt usage and optimization."""
        for i in range(20):
            # Simulate metrics updates
            for prompt_data in test_prompts:
                # Simulate performance metrics
                import random
                
                metrics = PromptMetrics(
                    success_rate=random.uniform(0.6, 0.95),
                    avg_execution_time=random.uniform(0.5, 3.0),
                    error_rate=random.uniform(0.0, 0.2),
                    avg_token_cost=random.uniform(0.001, 0.01),
                    sample_count=random.randint(1, 50)
                )
                
                # Update metrics
                tracker.record_metrics(prompt_data['id'], f"{prompt_data['id']}_v1", metrics)
                
                # Add streaming event
                await rt_system.add_streaming_event(
                    event_type='metrics_update',
                    prompt_id=prompt_data['id'],
                    data={
                        'metrics': {
                            'success_rate': metrics.success_rate,
                            'execution_time': metrics.avg_execution_time,
                            'error_rate': metrics.error_rate,
                            'composite_score': metrics.composite_score
                        },
                        'variant_id': f"{prompt_data['id']}_v1"
                    },
                    priority=5
                )
            
            # Trigger optimization every 5 iterations
            if i % 5 == 0:
                for prompt_data in test_prompts:
                    await rt_system.trigger_optimization(
                        prompt_id=prompt_data['id'],
                        priority=7,
                        context={'simulation': True, 'iteration': i}
                    )
            
            # Print status every 5 iterations
            if i % 5 == 0:
                status = rt_system.get_system_status()
                print(f"  📊 Iteration {i}: {status['stats']['optimizations_performed']} optimizations, "
                      f"{status['stats']['variants_switched']} switches, "
                      f"{status['stats']['alerts_generated']} alerts")
            
            await asyncio.sleep(2)  # Wait 2 seconds between iterations
    
    # Run simulation in background
    simulation_task = asyncio.create_task(simulate_usage())
    
    # Monitor system status
    print("\n📊 Monitoring system status...")
    
    try:
        for i in range(10):
            # Get system status
            status = rt_system.get_system_status()
            performance = rt_system.get_performance_summary()
            
            print(f"\n🔍 Status Check {i + 1}:")
            print(f"  🟢 System: {status['status']}")
            print(f"  ⏱️  Uptime: {status['uptime']:.1f}s")
            print(f"  🔄 Optimizations: {performance['optimizations_performed']}")
            print(f"  🔀 Variant Switches: {performance['variants_switched']}")
            print(f"  🚨 Active Alerts: {performance['active_alerts']}")
            print(f"  📡 Connected Clients: {performance['connected_clients']}")
            
            # Get component health
            health = await rt_system.health_check()
            print(f"  🏥 Overall Health: {health['overall']}")
            
            await asyncio.sleep(5)  # Check every 5 seconds
    
    except KeyboardInterrupt:
        print("\n⏹️  Stopping simulation...")
    
    # Stop simulation
    simulation_task.cancel()
    
    # Get final dashboard data
    print("\n📊 Final Dashboard Data:")
    dashboard_data = rt_system.get_dashboard_data()
    
    print(f"  🎯 Total Optimizations: {dashboard_data['performance_summary']['optimizations_performed']}")
    print(f"  🔀 Total Switches: {dashboard_data['performance_summary']['variants_switched']}")
    print(f"  🚨 Total Alerts: {dashboard_data['performance_summary']['alerts_generated']}")
    print(f"  📈 Events Processed: {dashboard_data['performance_summary']['events_processed']}")
    
    # Export system data
    export_file = f"realtime_optimization_export_{int(time.time())}.json"
    rt_system.export_system_data(export_file)
    print(f"  💾 Data exported to: {export_file}")
    
    # Stop the system
    print("\n🛑 Stopping real-time optimization system...")
    await rt_system.stop()
    
    print("✅ Real-time optimization system stopped!")
    print("\n🎉 Example completed successfully!")
    print("\nTo test the WebSocket interface:")
    print("1. Connect to ws://localhost:8765")
    print("2. Send: {'type': 'subscribe', 'subscription_type': 'metrics'}")
    print("3. Send: {'type': 'get_status'}")
    print("4. Send: {'type': 'trigger_optimization', 'prompt_id': 'system_prompt_1'}")


if __name__ == "__main__":
    asyncio.run(main())
