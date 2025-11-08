"""Cost Tracking Example

This example demonstrates how to monitor and control LLM costs in forge.
"""

import asyncio
from datetime import datetime, timedelta
import httpx


async def get_usage_stats(period='week'):
    """Get usage statistics for a time period."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:3000/api/analytics/usage?period={period}"
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📊 Usage Statistics ({period})")
            print("="*60)
            print(f"Conversations: {data.get('conversations', 0)}")
            print(f"Messages: {data.get('messages', 0)}")
            print(f"Total Cost: ${data.get('cost_usd', 0):.2f}")
            print(f"\nTokens:")
            print(f"  Input:  {data.get('tokens', {}).get('input', 0):,}")
            print(f"  Output: {data.get('tokens', {}).get('output', 0):,}")
            
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            return None


async def get_model_usage(period='week'):
    """Get per-model usage breakdown."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:3000/api/analytics/models?period={period}"
        )
        
        if response.status_code == 200:
            models = response.json()
            
            print(f"\n💰 Model Usage Breakdown ({period})")
            print("="*60)
            print(f"{'Model':<40} {'Convos':<10} {'Cost':>10}")
            print("-"*60)
            
            for model_data in models:
                model = model_data.get('model', 'unknown')[:38]
                convos = model_data.get('conversations', 0)
                cost = model_data.get('cost_usd', 0)
                print(f"{model:<40} {convos:<10} ${cost:>9.2f}")
            
            return models
        else:
            print(f"❌ Error: {response.status_code}")
            return None


async def monitor_realtime_costs():
    """Monitor costs in real-time during agent execution."""
    print("\n⏱️  Real-Time Cost Monitoring")
    print("="*60)
    print("Monitoring conversation costs every 5 seconds...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            async with httpx.AsyncClient() as client:
                # Get current metrics
                response = await client.get("http://localhost:3000/api/monitoring/metrics")
                
                if response.status_code == 200:
                    metrics = response.json()
                    system = metrics.get('system', {})
                    
                    # Calculate approximate costs
                    active = system.get('active_conversations', 0)
                    actions = system.get('total_actions_today', 0)
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"Active: {active} | "
                          f"Actions today: {actions}")
            
            await asyncio.sleep(5)
            
    except KeyboardInterrupt:
        print("\n✋ Monitoring stopped")


async def set_cost_limits():
    """Set daily cost limits to prevent overspending."""
    print("\n💸 Cost Limit Configuration")
    print("="*60)
    
    # Cost limits are configured in settings
    settings = {
        "cost_limits": {
            "daily_limit_usd": 1.00,      # $1/day for free tier
            "alert_threshold": 0.75,       # Alert at 75% of limit
            "hard_stop": True,             # Stop agent when limit reached
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.put(
            "http://localhost:3000/api/settings",
            json=settings
        )
        
        if response.status_code == 200:
            print("✅ Cost limits configured:")
            print(f"   Daily limit: ${settings['cost_limits']['daily_limit_usd']}")
            print(f"   Alert at: {settings['cost_limits']['alert_threshold']*100}%")
            print(f"   Hard stop: {settings['cost_limits']['hard_stop']}")
        else:
            print(f"❌ Error: {response.status_code}")


async def cost_optimization_tips():
    """Display cost optimization strategies."""
    print("\n💡 Cost Optimization Tips")
    print("="*60)
    
    tips = [
        {
            "title": "1. Use Cheaper Models for Simple Tasks",
            "current": "claude-sonnet-4 ($3/$15 per 1M tokens)",
            "optimized": "claude-haiku-4.5 ($1/$5 per 1M tokens)",
            "savings": "67% cheaper, 2x faster",
        },
        {
            "title": "2. Enable Prompt Caching",
            "current": "No caching ($0.05 per request)",
            "optimized": "Caching enabled ($0.01 per cached request)",
            "savings": "35-50% cost reduction",
        },
        {
            "title": "3. Reduce Context Size",
            "current": "max_message_chars=30000",
            "optimized": "max_message_chars=20000",
            "savings": "33% fewer input tokens",
        },
        {
            "title": "4. Use OpenRouter Free Models",
            "current": "Paid commercial models",
            "optimized": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
            "savings": "100% free (with rate limits)",
        }
    ]
    
    for tip in tips:
        print(f"\n{tip['title']}")
        print(f"  Current:   {tip['current']}")
        print(f"  Optimized: {tip['optimized']}")
        print(f"  Savings:   {tip['savings']}")


async def main_menu():
    """Interactive menu for cost tracking examples."""
    print("\n🎯 Forge Cost Tracking Examples")
    print("="*60)
    print("\nChoose an option:")
    print("1. Get usage statistics (week)")
    print("2. Get model usage breakdown")
    print("3. Monitor real-time costs")
    print("4. Set cost limits")
    print("5. Cost optimization tips")
    print("6. Exit")
    
    choice = input("\nEnter choice (1-6): ").strip()
    
    if choice == '1':
        await get_usage_stats('week')
    elif choice == '2':
        await get_model_usage('week')
    elif choice == '3':
        await monitor_realtime_costs()
    elif choice == '4':
        await set_cost_limits()
    elif choice == '5':
        await cost_optimization_tips()
    elif choice == '6':
        print("\n👋 Goodbye!")
        return
    else:
        print("❌ Invalid choice")
    
    # Show menu again
    await main_menu()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Forge Cost Tracking & Optimization")
    print("="*60)
    print("\nMake sure Forge is running: http://localhost:3000")
    print()
    
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n\n✋ Stopped by user")

