"""Offline Adaptation Example.

This example shows how to use ACE framework for offline training
on a dataset of tasks to build a comprehensive playbook.
"""

import json
from typing import TypedDict, List, cast

from forge.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig
from forge.llm.llm import LLM


class TrainingExample(TypedDict):
    query: str
    task_type: str
    role: str | None
    expected_outcome: str


def offline_adaptation_example():
    """Example of offline adaptation using ACE framework."""
    # Sample training data
    training_data: List[TrainingExample] = [
        {
            "query": "Implement user authentication system",
            "task_type": "metasop",
            "role": "engineer",
            "expected_outcome": "Secure authentication system with login/logout functionality",
        },
        {
            "query": "Add password validation rules",
            "task_type": "metasop",
            "role": "engineer",
            "expected_outcome": "Password validation with strength requirements",
        },
        {
            "query": "Implement session management",
            "task_type": "metasop",
            "role": "engineer",
            "expected_outcome": "Secure session handling with timeout",
        },
        {
            "query": "Add two-factor authentication",
            "task_type": "metasop",
            "role": "engineer",
            "expected_outcome": "2FA implementation with TOTP support",
        },
        {
            "query": "Write a Python function to calculate fibonacci numbers",
            "task_type": "code_generation",
            "role": None,
            "expected_outcome": "Efficient fibonacci function with memoization",
        },
        {
            "query": "Create a REST API endpoint for user management",
            "task_type": "code_generation",
            "role": None,
            "expected_outcome": "RESTful API with CRUD operations for users",
        },
    ]

    # Create ACE configuration
    config = ACEConfig(
        enable_ace=True,
        max_bullets=1000,
        multi_epoch=True,
        num_epochs=3,
        reflector_max_iterations=3,
        enable_online_adaptation=False,  # Disable for offline training
        playbook_persistence_path="offline_playbook.json",
    )

    # Create context playbook
    playbook = ContextPlaybook(max_bullets=1000)

    # Initialize ACE framework
    # Note: In real usage, you would provide an actual LLM instance
    ace = ACEFramework(
        llm=cast(LLM, None),  # Mock LLM for this example
        context_playbook=playbook,
        config=config,
    )

    print("Starting offline adaptation training...")
    print(f"Training on {len(training_data)} examples")
    print(f"Number of epochs: {config.num_epochs}")
    print("-" * 50)

    # Extract queries and metadata
    queries = [item["query"] for item in training_data]
    task_types = [item["task_type"] for item in training_data]
    roles = [item["role"] for item in training_data]
    expected_outcomes = [item["expected_outcome"] for item in training_data]

    # Run multi-epoch training
    results = ace.multi_epoch_training(
        queries=queries,
        task_type="mixed",  # Mixed task types
        roles=roles,
        ground_truths=expected_outcomes,
    )

    print(f"\nTraining completed!")
    print(f"Processed {len(results)} total examples")

    # Get performance summary
    performance = ace.get_performance_summary()

    print("\nPerformance Summary:")
    print(f"Total tasks: {performance['framework_metrics']['total_tasks']}")
    print(f"Successful tasks: {performance['framework_metrics']['successful_tasks']}")
    print(f"Success rate: {performance['framework_metrics']['success_rate']:.2f}")
    print(f"Context updates: {performance['framework_metrics']['context_updates']}")

    # Get playbook statistics
    playbook_stats = performance["playbook_statistics"]
    print(f"\nPlaybook Statistics:")
    print(f"Total bullets: {playbook_stats['total_bullets']}")
    print(f"Average helpfulness: {playbook_stats['avg_helpfulness']:.2f}")

    # Show section breakdown
    if "sections" in playbook_stats:
        print(f"\nSection Breakdown:")
        for section, stats in playbook_stats["sections"].items():
            print(
                f"  {section}: {stats['count']} bullets (avg helpfulness: {stats['avg_helpfulness']:.2f})"
            )

    # Save the trained playbook
    if ace.save_playbook("trained_playbook.json"):
        print(f"\nTrained playbook saved to 'trained_playbook.json'")

    # Show some example bullets from the playbook
    print(f"\nExample playbook content:")
    content = ace.context_playbook.get_playbook_content(max_bullets=10)
    print(content[:500] + "..." if len(content) > 500 else content)

    return ace, results


def load_and_use_trained_playbook():
    """Example of loading a trained playbook and using it for new tasks."""
    # Create new ACE framework
    config = ACEConfig(enable_ace=True, max_bullets=1000, enable_online_adaptation=True)

    playbook = ContextPlaybook(max_bullets=1000)
    ace = ACEFramework(
        llm=cast(LLM, None),  # Mock LLM for this example
        context_playbook=playbook,
        config=config,
    )

    # Load the trained playbook
    if ace.load_playbook("trained_playbook.json"):
        print("Successfully loaded trained playbook!")

        # Show playbook statistics
        stats = ace.context_playbook.get_statistics()
        print(f"Loaded playbook has {stats['total_bullets']} bullets")

        # Use the playbook for a new task
        result = ace.process_task(
            query="Implement OAuth authentication",
            task_type="metasop",
            role="engineer",
            expected_outcome="OAuth 2.0 implementation with Google/Apple providers",
        )

        print(f"New task result: Success={result.success}")
        print(f"Processing time: {result.processing_time:.2f}s")

    else:
        print("Failed to load trained playbook")


if __name__ == "__main__":
    print("ACE Framework - Offline Adaptation Example")
    print("=" * 50)

    # Run offline adaptation
    ace, results = offline_adaptation_example()

    print("\n" + "=" * 50)
    print("Loading and using trained playbook...")

    # Load and use trained playbook
    load_and_use_trained_playbook()
