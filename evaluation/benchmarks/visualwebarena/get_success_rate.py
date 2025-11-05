import argparse
import json
import logging
import gymnasium as gym

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser(description="Calculate average reward.")
parser.add_argument("output_path", type=str, help="path to output.jsonl")
args = parser.parse_args()
if __name__ == "__main__":
    env_ids = [id for id in gym.envs.registry.keys() if id.startswith("browsergym/visualwebarena")]
    total_num = len(env_ids)
    logger.info("Total number of tasks: %d", total_num)
    total_reward = 0
    total_cost = 0
    actual_num = 0
    with open(args.output_path, "r", encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            actual_num += 1
            total_cost += data["metrics"]["accumulated_cost"]
            reward = data["test_result"]["reward"]
            if reward >= 0:
                total_reward += data["test_result"]["reward"]
            else:
                actual_num -= 1
    avg_reward = total_reward / total_num
    logger.info("Total reward: %s", total_reward)
    logger.info("Success Rate: %s", avg_reward)
    avg_cost = total_cost / actual_num
    logger.info("Avg Cost: %s", avg_cost)
    logger.info("Total Cost: %s", total_cost)
    logger.info("Actual number of tasks finished: %d", actual_num)
