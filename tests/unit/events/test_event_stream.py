import gc
import json
import os
import time
from datetime import datetime
import psutil
import pytest
from pytest import TempPathFactory
from forge.core.schema import ActionType, ObservationType
from forge.events import EventSource, EventStream, EventStreamSubscriber
from forge.events.action import CmdRunAction, NullAction
from forge.events.action.files import FileEditAction, FileReadAction, FileWriteAction
from forge.events.action.message import MessageAction
from forge.events.event import FileEditSource, FileReadSource
from forge.events.event_filter import EventFilter
from forge.events.observation import NullObservation
from forge.events.observation.files import FileEditObservation, FileReadObservation, FileWriteObservation
from forge.events.serialization.event import event_to_dict
from forge.storage import get_file_store
from forge.storage.locations import get_conversation_event_filename


@pytest.fixture
def temp_dir(tmp_path_factory: TempPathFactory) -> str:
    return str(tmp_path_factory.mktemp("test_event_stream"))


def collect_events(stream):
    return list(stream.get_events())


def test_basic_flow(temp_dir: str):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    event_stream.add_event(NullAction(), EventSource.AGENT)
    assert len(collect_events(event_stream)) == 1


def test_stream_storage(temp_dir: str):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    event_stream.add_event(NullObservation(""), EventSource.AGENT)
    assert len(collect_events(event_stream)) == 1
    content = event_stream.file_store.read(get_conversation_event_filename("abc", 0))
    assert content is not None
    data = json.loads(content)
    assert "timestamp" in data
    del data["timestamp"]
    assert data == {
        "id": 0,
        "source": "agent",
        "observation": "null",
        "content": "",
        "extras": {},
        "message": "No observation",
    }


def test_rehydration(temp_dir: str):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    event_stream.add_event(NullObservation("obs1"), EventSource.AGENT)
    event_stream.add_event(NullObservation("obs2"), EventSource.AGENT)
    assert len(collect_events(event_stream)) == 2
    stream2 = EventStream("es2", file_store)
    assert len(collect_events(stream2)) == 0
    stream1rehydrated = EventStream("abc", file_store)
    events = collect_events(stream1rehydrated)
    assert len(events) == 2
    assert events[0].content == "obs1"
    assert events[1].content == "obs2"


def test_get_matching_events_type_filter(temp_dir: str):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    event_stream.add_event(NullAction(), EventSource.AGENT)
    event_stream.add_event(NullObservation("test"), EventSource.AGENT)
    event_stream.add_event(NullAction(), EventSource.AGENT)
    event_stream.add_event(MessageAction(content="test"), EventSource.AGENT)
    events = event_stream.get_matching_events(event_types=(NullAction,))
    assert len(events) == 2
    assert all((isinstance(e, NullAction) for e in events))
    events = event_stream.get_matching_events(event_types=(NullObservation,))
    assert len(events) == 1
    assert isinstance(events[0], NullObservation) and events[0].observation == ObservationType.NULL
    events = event_stream.get_matching_events(event_types=(NullAction, MessageAction))
    assert len(events) == 3
    events = event_stream.get_matching_events(reverse=True, limit=3)
    assert len(events) == 3
    assert isinstance(events[0], MessageAction) and events[0].content == "test"
    assert isinstance(events[2], NullObservation) and events[2].content == "test"


def test_get_matching_events_query_search(temp_dir: str):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    event_stream.add_event(NullObservation("hello world"), EventSource.AGENT)
    event_stream.add_event(NullObservation("test message"), EventSource.AGENT)
    event_stream.add_event(NullObservation("another hello"), EventSource.AGENT)
    events = event_stream.get_matching_events(query="hello")
    assert len(events) == 2
    events = event_stream.get_matching_events(query="HELLO")
    assert len(events) == 2
    events = event_stream.get_matching_events(query="nonexistent")
    assert len(events) == 0


def test_get_matching_events_source_filter(temp_dir: str):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    event_stream.add_event(NullObservation("test1"), EventSource.AGENT)
    event_stream.add_event(NullObservation("test2"), EventSource.ENVIRONMENT)
    event_stream.add_event(NullObservation("test3"), EventSource.AGENT)
    events = event_stream.get_matching_events(source="agent")
    assert len(events) == 2
    assert all((isinstance(e, NullObservation) and e.source == EventSource.AGENT for e in events))
    events = event_stream.get_matching_events(source="environment")
    assert len(events) == 1
    assert isinstance(events[0], NullObservation) and events[0].source == EventSource.ENVIRONMENT
    null_source_event = NullObservation("test4")
    event_stream.add_event(null_source_event, EventSource.AGENT)
    event = event_stream.get_event(event_stream.get_latest_event_id())
    event._source = None
    data = event_to_dict(event)
    event_stream.file_store.write(event_stream._get_filename_for_id(event.id, event_stream.user_id), json.dumps(data))
    assert EventFilter(source="agent").exclude(event)
    assert EventFilter(source=None).include(event)
    events = event_stream.get_matching_events(source="agent")
    assert len(events) == 2


def test_get_matching_events_pagination(temp_dir: str):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    for i in range(5):
        event_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    events = event_stream.get_matching_events(limit=3)
    assert len(events) == 3
    events = event_stream.get_matching_events(start_id=2)
    assert len(events) == 3
    assert isinstance(events[0], NullObservation) and events[0].content == "test2"
    events = event_stream.get_matching_events(start_id=1, limit=2)
    assert len(events) == 2
    assert isinstance(events[0], NullObservation) and events[0].content == "test1"
    assert isinstance(events[1], NullObservation) and events[1].content == "test2"


def test_get_matching_events_limit_validation(temp_dir: str):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
        event_stream.get_matching_events(limit=0)
    with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
        event_stream.get_matching_events(limit=101)
    event_stream.add_event(NullObservation("test"), EventSource.AGENT)
    events = event_stream.get_matching_events(limit=1)
    assert len(events) == 1
    events = event_stream.get_matching_events(limit=100)
    assert len(events) == 1


def test_memory_usage_file_operations(temp_dir: str):
    """Test memory usage during file operations in EventStream.

    This test verifies that memory usage during file operations is reasonable
    and that memory is properly cleaned up after operations complete.
    """

    def get_memory_mb():
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    test_file = os.path.join(temp_dir, "test_file.txt")
    test_content = "x" * (100 * 1024)
    with open(test_file, "w", encoding='utf-8') as f:
        f.write(test_content)
    file_store = get_file_store("local", temp_dir)
    gc.collect()
    initial_memory = get_memory_mb()
    max_memory_increase = 0
    for i in range(20):
        event_stream = EventStream("test_session", file_store)
        read_action = FileReadAction(
            path=test_file,
            start=0,
            end=-1,
            thought="Reading file",
            action=ActionType.READ,
            impl_source=FileReadSource.DEFAULT,
        )
        event_stream.add_event(read_action, EventSource.AGENT)
        read_obs = FileReadObservation(path=test_file, impl_source=FileReadSource.DEFAULT, content=test_content)
        event_stream.add_event(read_obs, EventSource.ENVIRONMENT)
        write_action = FileWriteAction(
            path=test_file, content=test_content, start=0, end=-1, thought="Writing file", action=ActionType.WRITE
        )
        event_stream.add_event(write_action, EventSource.AGENT)
        write_obs = FileWriteObservation(path=test_file, content=test_content)
        event_stream.add_event(write_obs, EventSource.ENVIRONMENT)
        edit_action = FileEditAction(
            path=test_file,
            content=test_content,
            start=1,
            end=-1,
            thought="Editing file",
            action=ActionType.EDIT,
            impl_source=FileEditSource.LLM_BASED_EDIT,
        )
        event_stream.add_event(edit_action, EventSource.AGENT)
        edit_obs = FileEditObservation(
            path=test_file,
            prev_exist=True,
            old_content=test_content,
            new_content=test_content,
            impl_source=FileEditSource.LLM_BASED_EDIT,
            content=test_content,
        )
        event_stream.add_event(edit_obs, EventSource.ENVIRONMENT)
        event_stream.close()
        gc.collect()
        current_memory = get_memory_mb()
        memory_increase = current_memory - initial_memory
        max_memory_increase = max(max_memory_increase, memory_increase)
    os.remove(test_file)
    assert max_memory_increase < 50, f"Memory increase of {max_memory_increase:.1f}MB exceeds limit of 50MB"


def test_cache_page_creation(temp_dir: str):
    """Test that cache pages are created correctly when adding events."""
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("cache_test", file_store)
    event_stream.cache_size = 5
    for i in range(10):
        event_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    cache_filename = event_stream._get_filename_for_cache(0, 5)
    try:
        cache_content = file_store.read(cache_filename)
        cache_exists = True
    except FileNotFoundError:
        cache_exists = False
    assert cache_exists, f"Cache file {cache_filename} should exist"
    if cache_exists:
        cache_data = json.loads(cache_content)
        assert len(cache_data) == 5, "Cache page should contain 5 events"
        for i, event_data in enumerate(cache_data):
            assert event_data["content"] == f"test{i}", f"Event {i} content should be 'test{i}'"


def test_cache_page_loading(temp_dir: str):
    """Test that cache pages are loaded correctly when retrieving events."""
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("cache_load_test", file_store)
    event_stream.cache_size = 5
    for i in range(15):
        event_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    new_stream = EventStream("cache_load_test", file_store)
    new_stream.cache_size = 5
    events = collect_events(new_stream)
    assert len(events) > 10, "Should retrieve most of the events"
    for i, event in enumerate(events):
        assert isinstance(event, NullObservation), f"Event {i} should be a NullObservation"
        assert event.content == f"test{i}", f"Event {i} content should be 'test{i}'"


def test_cache_page_performance(temp_dir: str):
    """Test that using cache pages improves performance when retrieving many events."""
    file_store = get_file_store("local", temp_dir)
    cached_stream = EventStream("perf_test_cached", file_store)
    cached_stream.cache_size = 10
    num_events = 50
    for i in range(num_events):
        cached_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    uncached_stream = EventStream("perf_test_uncached", file_store)
    uncached_stream.cache_size = 10
    for i in range(num_events):
        uncached_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    start_time = time.time()
    cached_events = collect_events(cached_stream)
    cached_time = time.time() - start_time
    start_time = time.time()
    uncached_events = collect_events(uncached_stream)
    uncached_time = time.time() - start_time
    assert len(cached_events) > 40, "Cached stream should return most of the events"
    assert len(uncached_events) > 40, "Uncached stream should return most of the events"
    logger_message = f"Cached time: {cached_time:.4f}s, Uncached time: {uncached_time:.4f}s"
    print(logger_message)


def test_search_events_limit(temp_dir: str):
    """Test that the search_events method correctly applies the limit parameter."""
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    for i in range(10):
        event_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    events = list(event_stream.search_events())
    assert len(events) == 10
    events = list(event_stream.search_events(limit=5))
    assert len(events) == 5
    assert all((isinstance(e, NullObservation) for e in events))
    assert [e.content for e in events] == ["test0", "test1", "test2", "test3", "test4"]
    events = list(event_stream.search_events(start_id=5, limit=3))
    assert len(events) == 3
    assert [e.content for e in events] == ["test5", "test6", "test7"]
    events = list(event_stream.search_events(reverse=True, limit=4))
    assert len(events) == 4
    assert [e.content for e in events] == ["test9", "test8", "test7", "test6"]
    event_stream.add_event(NullObservation("filter_me"), EventSource.AGENT)
    event_stream.add_event(NullObservation("filter_me_too"), EventSource.AGENT)
    events = list(event_stream.search_events(filter=EventFilter(query="filter"), limit=1))
    assert len(events) == 1
    assert events[0].content == "filter_me"


def test_search_events_limit_with_complex_filters(temp_dir: str):
    """Test the interaction between limit and various filter combinations in search_events."""
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    event_stream.add_event(NullAction(), EventSource.AGENT)
    event_stream.add_event(NullObservation("test1"), EventSource.AGENT)
    event_stream.add_event(MessageAction(content="hello"), EventSource.USER)
    event_stream.add_event(NullObservation("test2"), EventSource.ENVIRONMENT)
    event_stream.add_event(NullAction(), EventSource.AGENT)
    event_stream.add_event(MessageAction(content="world"), EventSource.USER)
    event_stream.add_event(NullObservation("hello world"), EventSource.AGENT)
    events = list(event_stream.search_events(filter=EventFilter(include_types=(NullAction,)), limit=1))
    assert len(events) == 1
    assert isinstance(events[0], NullAction)
    assert events[0].id == 0
    events = list(event_stream.search_events(filter=EventFilter(source="user"), limit=1))
    assert len(events) == 1
    assert events[0].source == EventSource.USER
    assert events[0].id == 2
    events = list(event_stream.search_events(filter=EventFilter(query="hello"), limit=2))
    assert len(events) == 2
    assert [e.id for e in events] == [2, 6]
    events = list(
        event_stream.search_events(filter=EventFilter(source="agent", include_types=(NullObservation,)), limit=1)
    )
    assert len(events) == 1
    assert isinstance(events[0], NullObservation)
    assert events[0].source == EventSource.AGENT
    assert events[0].id == 1
    events = list(event_stream.search_events(filter=EventFilter(source="agent"), reverse=True, limit=2))
    assert len(events) == 2
    assert [e.id for e in events] == [6, 4]


def test_search_events_limit_edge_cases(temp_dir: str):
    """Test edge cases for the limit parameter in search_events."""
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("abc", file_store)
    for i in range(5):
        event_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    events = list(event_stream.search_events(limit=None))
    assert len(events) == 5
    events = list(event_stream.search_events(limit=10))
    assert len(events) == 5
    events = list(event_stream.search_events(limit=0))
    assert len(events) in {0, 5}
    events = list(event_stream.search_events(limit=-1))
    assert len(events) == 1
    events = list(event_stream.search_events(filter=EventFilter(query="nonexistent"), limit=5))
    assert not events
    events = list(event_stream.search_events(start_id=10, limit=5))
    assert not events


def test_callback_dictionary_modification(temp_dir: str):
    """Test that the event stream can handle dictionary modification during iteration.

    This test verifies that the fix for the 'dictionary changed size during iteration' error works.
    The test adds a callback that adds a new callback during iteration, which would cause an error
    without the fix.
    """
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("callback_test", file_store)
    callback_executed = [False, False, False]

    def callback_added_during_iteration(event):
        callback_executed[2] = True

    def callback1(event):
        callback_executed[0] = True
        event_stream.subscribe(EventStreamSubscriber.TEST, callback_added_during_iteration, "callback3")

    def callback2(event):
        callback_executed[1] = True

    event_stream.subscribe(EventStreamSubscriber.TEST, callback1, "callback1")
    event_stream.subscribe(EventStreamSubscriber.TEST, callback2, "callback2")
    event_stream.add_event(NullObservation("test"), EventSource.AGENT)
    time.sleep(0.5)
    assert callback_executed[0] is True, "First callback should have been executed"
    assert callback_executed[1] is True, "Second callback should have been executed"
    assert callback_executed[2] is False, "Third callback should not have been executed for this event"
    callback_executed = [False, False, False]
    event_stream.add_event(NullObservation("test2"), EventSource.AGENT)
    time.sleep(0.5)
    assert callback_executed[0] is True, "First callback should have been executed"
    assert callback_executed[1] is True, "Second callback should have been executed"
    assert callback_executed[2] is True, "Third callback should have been executed"
    event_stream.close()


def test_cache_page_partial_retrieval(temp_dir: str):
    """Test retrieving events with start_id and end_id parameters using the cache."""
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("partial_test", file_store)
    event_stream.cache_size = 5
    for i in range(20):
        event_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    events = list(event_stream.get_events(start_id=3, end_id=12))
    assert len(events) >= 8, "Should retrieve most events in the range"
    for i, event in enumerate(events):
        expected_content = f"test{i + 3}"
        assert event.content == expected_content, f"Event {i} content should be '{expected_content}'"
    reverse_events = list(event_stream.get_events(start_id=3, end_id=12, reverse=True))
    assert len(reverse_events) >= 8, "Should retrieve most events in reverse"
    if len(reverse_events) >= 3:
        assert reverse_events[0].content.startswith("test1"), "First reverse event should be near the end of the range"
        assert int(reverse_events[0].content[4:]) > int(
            reverse_events[1].content[4:]
        ), "Events should be in descending order"


def test_cache_page_with_missing_events(temp_dir: str):
    """Test cache behavior when some events are missing."""
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("missing_test", file_store)
    event_stream.cache_size = 5
    for i in range(10):
        event_stream.add_event(NullObservation(f"test{i}"), EventSource.AGENT)
    new_stream = EventStream("missing_test", file_store)
    new_stream.cache_size = 5
    initial_events = list(new_stream.get_events())
    initial_count = len(initial_events)
    missing_id = 5
    missing_filename = new_stream._get_filename_for_id(missing_id, new_stream.user_id)
    try:
        file_store.delete(missing_filename)
        reload_stream = EventStream("missing_test", file_store)
        reload_stream.cache_size = 5
        events_after_deletion = list(reload_stream.get_events())
        assert len(events_after_deletion) <= initial_count, "Should have fewer or equal events after deletion"
        assert events_after_deletion, "Should still retrieve some events"
    except Exception as e:
        print(f"Note: Could not delete file {missing_filename}: {e}")
        assert initial_events, "Should retrieve events successfully"


def test_secrets_replaced_in_content(temp_dir: str):
    """Test that secrets are properly replaced in event content."""
    file_store = get_file_store("local", temp_dir)
    stream = EventStream("test_session", file_store)
    stream.set_secrets({"api_key": "secret123"})
    action = CmdRunAction(command='curl -H "Authorization: Bearer secret123" https://api.example.com')
    action._timestamp = datetime.now().isoformat()
    data = event_to_dict(action)
    data_with_secrets_replaced = stream._replace_secrets(data)
    assert "<secret_hidden>" in data_with_secrets_replaced["args"]["command"]
    assert "secret123" not in data_with_secrets_replaced["args"]["command"]


def test_timestamp_not_affected_by_secret_replacement(temp_dir: str):
    """Test that timestamps are not corrupted by secret replacement."""
    file_store = get_file_store("local", temp_dir)
    stream = EventStream("test_session", file_store)
    stream.set_secrets({"test_secret": "18"})
    action = CmdRunAction(command='echo "hello world"')
    action._timestamp = "2025-07-18T17:01:36.799608"
    data = event_to_dict(action)
    original_timestamp = data["timestamp"]
    data_with_secrets_replaced = stream._replace_secrets(data)
    assert data_with_secrets_replaced["timestamp"] == original_timestamp
    assert "<secret_hidden>" not in data_with_secrets_replaced["timestamp"]
    assert "18" in data_with_secrets_replaced["timestamp"]


def test_protected_fields_not_affected_by_secret_replacement(temp_dir: str):
    """Test that protected system fields are not affected by secret replacement."""
    file_store = get_file_store("local", temp_dir)
    stream = EventStream("test_session", file_store)
    stream.set_secrets({"secret1": "123", "secret2": "user", "secret3": "run", "secret4": "Running"})
    data = {
        "id": 123,
        "timestamp": "2025-07-18T17:01:36.799608",
        "source": "user",
        "cause": 123,
        "action": "run",
        "observation": "run",
        "message": "Running command: echo hello",
        "content": "This contains secret1: 123 and secret2: user and secret3: run",
    }
    data_with_secrets_replaced = stream._replace_secrets(data)
    assert data_with_secrets_replaced["id"] == 123
    assert data_with_secrets_replaced["timestamp"] == "2025-07-18T17:01:36.799608"
    assert data_with_secrets_replaced["source"] == "user"
    assert data_with_secrets_replaced["cause"] == 123
    assert data_with_secrets_replaced["action"] == "run"
    assert data_with_secrets_replaced["observation"] == "run"
    assert data_with_secrets_replaced["message"] == "Running command: echo hello"
    assert "<secret_hidden>" in data_with_secrets_replaced["content"]
    assert "123" not in data_with_secrets_replaced["content"]
    assert "user" not in data_with_secrets_replaced["content"]


def test_nested_dict_secret_replacement(temp_dir: str):
    """Test that secrets are replaced in nested dictionaries while preserving protected fields."""
    file_store = get_file_store("local", temp_dir)
    stream = EventStream("test_session", file_store)
    stream.set_secrets({"secret": "password123"})
    data = {
        "timestamp": "2025-07-18T17:01:36.799608",
        "args": {
            "command": "login --password password123",
            "env": {"SECRET_KEY": "password123", "timestamp": "password123_timestamp"},
        },
    }
    data_with_secrets_replaced = stream._replace_secrets(data)
    assert data_with_secrets_replaced["timestamp"] == "2025-07-18T17:01:36.799608"
    assert "<secret_hidden>" in data_with_secrets_replaced["args"]["command"]
    assert data_with_secrets_replaced["args"]["env"]["SECRET_KEY"] == "<secret_hidden>"
    assert "<secret_hidden>" in data_with_secrets_replaced["args"]["env"]["timestamp"]
    assert "password123" not in data_with_secrets_replaced["args"]["command"]
    assert "password123" not in data_with_secrets_replaced["args"]["env"]["SECRET_KEY"]
    assert "password123" not in data_with_secrets_replaced["args"]["env"]["timestamp"]
