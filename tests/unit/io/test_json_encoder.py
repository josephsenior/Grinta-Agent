import gc
from datetime import datetime
import psutil
from openhands.io.json import dumps


def get_memory_usage():
    """Get current memory usage of the process."""
    process = psutil.Process()
    return process.memory_info().rss


def test_json_encoder_memory_leak():
    gc.collect()
    initial_memory = get_memory_usage()
    large_data = {"datetime": datetime.now(), "nested": [{"timestamp": datetime.now()} for _ in range(1000)]}
    memory_samples = []
    for _ in range(10):
        for _ in range(100):
            dumps(large_data)
            dumps(large_data, indent=2)
        gc.collect()
        memory_samples.append(get_memory_usage())
    max_memory = max(memory_samples)
    min_memory = min(memory_samples)
    memory_variation = max_memory - min_memory
    assert memory_variation < 2 * 1024 * 1024, f"Memory usage unstable: {memory_variation} bytes variation"
    final_memory = memory_samples[-1]
    memory_increase = final_memory - initial_memory
    assert memory_increase < 2 * 1024 * 1024, f"Memory leak detected: {memory_increase} bytes increase"
