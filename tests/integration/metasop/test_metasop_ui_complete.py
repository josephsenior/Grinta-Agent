#!/usr/bin/env python3
"""Test MetaSOP UI integration by simulating a WebSocket message."""

import asyncio
import json
import os
import socketio
import sys
from typing import Any

# Add the Forge directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_metasop_ui_message():
    """Test MetaSOP by sending a WebSocket message like the UI would."""
    print("Testing MetaSOP UI integration via WebSocket...")

    # Create Socket.IO client
    sio = socketio.AsyncClient()

    # Track received events
    received_events = []

    @sio.event
    async def connect():
        """Report successful connection to Forge server."""
        print("Connected to Forge server")

    @sio.event
    async def disconnect():
        """Report disconnection from Forge server."""
        print("Disconnected from server")

    @sio.event
    async def oh_event(data: Any):
        """Handle oh_event messages from the server."""
        print(f"Received oh_event: {data}")
        received_events.append(data)

    try:
        await sio.connect("http://localhost:3000")
        print("Connected successfully")
        await asyncio.sleep(1)

        payload = {
            "action": "message",
            "args": {
                "content": "sop: Generate a README for the project",
                "image_urls": [],
                "file_urls": [],
                "timestamp": "2025-01-04T22:05:00.000Z",
            },
        }
        print(f"Sending payload: {json.dumps(payload, indent=2)}")
        await sio.emit("oh_user_action", payload)
        await asyncio.sleep(5)
        print(f"Received {len(received_events)} events from server")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"Encountered error: {exc}")
    finally:
        await sio.disconnect()


if __name__ == "__main__":
    asyncio.run(test_metasop_ui_message())
