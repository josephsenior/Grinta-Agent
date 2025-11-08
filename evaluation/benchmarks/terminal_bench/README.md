# Terminal-Bench Evaluation on Forge

Terminal-Bench has its own evaluation harness that is very different from forge'. We
implemented [Forge agent](https://github.com/laude-institute/terminal-bench/tree/main/terminal_bench/agents/installed_agents/Forge) using Forge local runtime
inside terminal-bench framework. Hereby we introduce how to use the terminal-bench
harness to evaluate Forge.

## Installation

Terminal-bench ships a CLI tool to manage tasks and run evaluation.
Please follow official [Installation Doc](https://www.tbench.ai/docs/installation). You could also clone terminal-bench [source code](https://github.com/laude-institute/terminal-bench) and use `uv run tb` CLI.

## Evaluation

Please see [Terminal-Bench Leaderboard](https://www.tbench.ai/leaderboard) for the latest
instruction on benchmarking guidance. The dataset might evolve.

Sample command:

```bash
export LLM_BASE_URL=<optional base url>
export LLM_API_KEY=<llm key>
tb run \
    --dataset-name terminal-bench-core \
    --dataset-version 0.1.1 \
    --agent Forge \
    --model <model> \
    --cleanup
```

You could run `tb --help` or `tb run --help` to learn more about their CLI.
