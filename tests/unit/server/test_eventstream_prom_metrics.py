from __future__ import annotations

from unittest.mock import MagicMock

from forge.events.stream import EventStream, get_aggregated_event_stream_stats


def test_eventstream_metrics_prometheus_lines(monkeypatch):
    file_store = MagicMock()
    file_store.list.return_value = []
    file_store.write = MagicMock()
    file_store.read = MagicMock()

    stream = EventStream("sid-metrics", file_store, user_id=None)

    try:
        stream._stats["enqueued"] = 5
        stream._stats["dropped_newest"] = 2
        stream._queue_size = 2

        stats = get_aggregated_event_stream_stats()
        text = "\n".join(
            [
                "# HELP forge_eventstream_streams Number of active EventStream instances",
                f"forge_eventstream_streams {stats.get('streams', 0)}",
                "# HELP forge_eventstream_queue_size Total enqueued events currently buffered across streams",
                f"forge_eventstream_queue_size {stats.get('queue_size', 0)}",
                "# HELP forge_eventstream_enqueued_total Events successfully enqueued (cumulative)",
                f"forge_eventstream_enqueued_total {stats.get('enqueued', 0)}",
                "# HELP forge_eventstream_dropped_newest_total Events dropped due to full queue (newest)",
                f"forge_eventstream_dropped_newest_total {stats.get('dropped_newest', 0)}",
            ]
        )
        # Assert metrics lines exist
        assert any(
            line.startswith("forge_eventstream_streams ") for line in text.splitlines()
        )
        assert any(
            line.startswith("forge_eventstream_queue_size ")
            for line in text.splitlines()
        )
        assert any(
            line.startswith("forge_eventstream_enqueued_total ")
            for line in text.splitlines()
        )
        assert any(
            line.startswith("forge_eventstream_dropped_newest_total ")
            for line in text.splitlines()
        )
    finally:
        stream.close()
