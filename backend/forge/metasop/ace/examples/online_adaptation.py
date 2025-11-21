"""Online Adaptation Example.

This example shows how to use ACE framework for real-time learning
during task execution, where the agent improves its performance
as it encounters new situations.
"""

from typing import TypedDict, List, cast

from forge.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig
from forge.llm.llm import LLM


class OnlineTask(TypedDict):
    query: str
    task_type: str
    role: str | None
    description: str


def online_adaptation_example():
    """Example of online adaptation using ACE framework."""
    # Create ACE configuration for online learning
    config = ACEConfig(
        enable_ace=True,
        max_bullets=500,
        multi_epoch=False,  # Disable for online learning
        enable_online_adaptation=True,
        playbook_persistence_path="online_playbook.json",
    )

    # Create context playbook
    playbook = ContextPlaybook(max_bullets=500)

    # Initialize ACE framework
    # Note: In real usage, you would provide an actual LLM instance
    ace = ACEFramework(
        llm=cast(LLM, None),  # Mock LLM for this example
        context_playbook=playbook,
        config=config,
    )

    print("Starting online adaptation example...")
    print("The agent will learn and improve as it processes tasks")
    print("-" * 50)

    # Simulate a series of related tasks that build upon each other
    tasks: List[OnlineTask] = [
        {
            "query": "Create a simple web server",
            "task_type": "code_generation",
            "role": None,
            "description": "Basic HTTP server setup",
        },
        {
            "query": "Add routing to the web server",
            "task_type": "code_generation",
            "role": None,
            "description": "URL routing functionality",
        },
        {
            "query": "Add middleware for authentication",
            "task_type": "code_generation",
            "role": None,
            "description": "Authentication middleware",
        },
        {
            "query": "Add error handling to the web server",
            "task_type": "code_generation",
            "role": None,
            "description": "Comprehensive error handling",
        },
        {
            "query": "Add logging to the web server",
            "task_type": "code_generation",
            "role": None,
            "description": "Request/response logging",
        },
    ]

    # Process each task and show learning progression
    for i, task in enumerate(tasks, 1):
        print(f"\nTask {i}: {task['description']}")
        print(f"Query: {task['query']}")

        # Process the task
        result = ace.process_task(
            query=task["query"], task_type=task["task_type"], role=task["role"]
        )

        print(f"Result: Success={result.success}, Time={result.processing_time:.2f}s")

        # Show playbook growth
        playbook_size = len(ace.context_playbook.bullets)
        print(f"Playbook size: {playbook_size} bullets")

        # Show performance metrics every few tasks
        if i % 2 == 0:
            metrics = ace.get_performance_summary()
            success_rate = metrics["framework_metrics"]["success_rate"]
            print(f"Current success rate: {success_rate:.2f}")

    print(f"\n" + "=" * 50)
    print("Online adaptation completed!")

    # Show final statistics
    final_metrics = ace.get_performance_summary()
    playbook_stats = final_metrics["playbook_statistics"]

    print(f"\nFinal Statistics:")
    print(f"Total tasks processed: {final_metrics['framework_metrics']['total_tasks']}")
    print(f"Success rate: {final_metrics['framework_metrics']['success_rate']:.2f}")
    print(f"Context updates: {final_metrics['framework_metrics']['context_updates']}")
    print(f"Final playbook size: {playbook_stats['total_bullets']} bullets")
    print(f"Average helpfulness: {playbook_stats['avg_helpfulness']:.2f}")

    # Show learned strategies
    print(f"\nLearned Strategies:")
    content = ace.context_playbook.get_playbook_content(max_bullets=15)
    print(content)

    # Save the final playbook
    if ace.save_playbook("final_online_playbook.json"):
        print(f"\nFinal playbook saved to 'final_online_playbook.json'")

    return ace


def demonstrate_learning_improvement():
    """Demonstrate how the agent improves over time."""
    print("\n" + "=" * 50)
    print("Demonstrating Learning Improvement")
    print("=" * 50)

    # Create ACE framework
    config = ACEConfig(enable_ace=True, max_bullets=200, enable_online_adaptation=True)

    playbook = ContextPlaybook(max_bullets=200)
    ace = ACEFramework(
        llm=cast(LLM, None),  # Mock LLM for this example
        context_playbook=playbook,
        config=config,
    )

    # Simulate repeated similar tasks to show learning
    similar_tasks = [
        "Write a function to sort a list of numbers",
        "Write a function to sort a list of strings",
        "Write a function to sort a list of objects by name",
        "Write a function to sort a list of objects by age",
        "Write a function to sort a list of objects by multiple criteria",
    ]

    print("Processing similar tasks to demonstrate learning...")

    for i, task in enumerate(similar_tasks, 1):
        print(f"\nTask {i}: {task}")

        result = ace.process_task(query=task, task_type="code_generation")

        # Show how playbook grows with similar tasks
        playbook_size = len(ace.context_playbook.bullets)
        print(f"Playbook size: {playbook_size} bullets")

        # Show success rate improvement
        metrics = ace.get_performance_summary()
        success_rate = metrics["framework_metrics"]["success_rate"]
        print(f"Success rate: {success_rate:.2f}")

    print(f"\nLearning demonstration completed!")
    print(f"Final playbook size: {len(ace.context_playbook.bullets)} bullets")

    # Show what the agent learned
    print(f"\nWhat the agent learned:")
    learned_strategies = ace.context_playbook.get_relevant_bullets("sorting", limit=5)
    for strategy in learned_strategies:
        print(f"  - {strategy.content}")


if __name__ == "__main__":
    print("ACE Framework - Online Adaptation Example")
    print("=" * 50)

    # Run online adaptation
    ace = online_adaptation_example()

    # Demonstrate learning improvement
    demonstrate_learning_improvement()
