"""Test for port allocation race condition fix."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.runtime.utils.port_lock import PortLock, find_available_port_with_lock


class TestPortLockingFix:
    """Test cases for port allocation race condition fix."""

    def test_port_lock_prevents_duplicate_allocation(self):
        """Test that port locking prevents duplicate port allocation."""
        allocated_ports = []
        port_locks = []

        def allocate_port():
            """Simulate port allocation by multiple workers."""
            result = find_available_port_with_lock(
                min_port=30000,
                max_port=30010,
                max_attempts=5,
                bind_address="0.0.0.0",
                lock_timeout=2.0,  # nosec B104 - Safe: test
            )
            if result:
                port, lock = result
                allocated_ports.append(port)
                port_locks.append(lock)
                time.sleep(0.1)
                return port
            return None

        num_workers = 8
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(allocate_port) for _ in range(num_workers)]
            results = [future.result() for future in as_completed(futures)]
        successful_ports = [port for port in results if port is not None]
        assert len(successful_ports) == len(set(successful_ports)), (
            f"Duplicate ports allocated: {successful_ports}"
        )
        for lock in port_locks:
            if lock:
                lock.release()
        print(
            f"Successfully allocated {len(successful_ports)} unique ports: {successful_ports}"
        )

    def test_port_lock_basic_functionality(self):
        """Test basic port lock functionality."""
        port = 30001
        lock1 = PortLock(port)
        assert lock1.acquire(timeout=1.0)
        assert lock1.is_locked
        lock2 = PortLock(port)
        assert not lock2.acquire(timeout=0.1)
        assert not lock2.is_locked
        lock1.release()
        assert not lock1.is_locked
        assert lock2.acquire(timeout=1.0)
        assert lock2.is_locked
        lock2.release()

    def test_port_lock_context_manager(self):
        """Test port lock context manager functionality."""
        port = 30002
        with PortLock(port) as lock:
            assert lock.is_locked
            lock2 = PortLock(port)
            assert not lock2.acquire(timeout=0.1)
        assert not lock.is_locked
        lock3 = PortLock(port)
        assert lock3.acquire(timeout=1.0)
        lock3.release()

    def test_concurrent_port_allocation_stress_test(self):
        """Stress test concurrent port allocation."""
        allocated_ports = []
        port_locks = []
        errors = []

        def worker_allocate_port(worker_id):
            """Worker function that allocates a port."""
            try:
                result = find_available_port_with_lock(
                    min_port=31000,
                    max_port=31020,
                    max_attempts=10,
                    bind_address="0.0.0.0",
                    lock_timeout=3.0,  # nosec B104 - Safe: test
                )
                if result:
                    port, lock = result
                    allocated_ports.append((worker_id, port))
                    port_locks.append(lock)
                    time.sleep(0.05)
                    return port
                else:
                    errors.append(f"Worker {worker_id}: No port available")
                    return None
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
                return None

        num_workers = 15
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(worker_allocate_port, i): i for i in range(num_workers)
            }
            results = {}
            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    result = future.result()
                    results[worker_id] = result
                except Exception as e:
                    errors.append(f"Worker {worker_id} exception: {str(e)}")
        successful_allocations = [
            (wid, port) for wid, port in allocated_ports if port is not None
        ]
        allocated_port_numbers = [port for _, port in successful_allocations]
        print(f"Successful allocations: {len(successful_allocations)}")
        print(f"Allocated ports: {allocated_port_numbers}")
        print(f"Errors: {len(errors)}")
        if errors:
            print(f"Error details: {errors[:5]}")
        unique_ports = set(allocated_port_numbers)
        assert len(allocated_port_numbers) == len(unique_ports), (
            f"Duplicate ports found: {allocated_port_numbers}"
        )
        for lock in port_locks:
            if lock:
                lock.release()

    def test_port_allocation_without_locking_shows_race_condition(self):
        """Test that demonstrates race condition without locking."""
        from backend.runtime.utils import find_available_tcp_port

        allocated_ports = []

        def allocate_port_without_lock():
            """Simulate port allocation without locking (old method)."""
            port = find_available_tcp_port(32000, 32010)
            allocated_ports.append(port)
            time.sleep(0.01)
            return port

        num_workers = 10
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(allocate_port_without_lock) for _ in range(num_workers)
            ]
            results = [future.result() for future in as_completed(futures)]
        unique_ports = set(results)
        duplicates_found = len(results) != len(unique_ports)
        print(
            f"Without locking - Total ports: {len(results)}, Unique: {len(unique_ports)}"
        )
        print(f"Ports allocated: {results}")
        print(f"Race condition detected: {duplicates_found}")
        assert len(results) == num_workers


if __name__ == "__main__":
    test = TestPortLockingFix()
    test.test_port_lock_prevents_duplicate_allocation()
    test.test_port_lock_basic_functionality()
    test.test_port_lock_context_manager()
    test.test_concurrent_port_allocation_stress_test()
    test.test_port_allocation_without_locking_shows_race_condition()
    print("All tests passed!")
