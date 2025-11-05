#!/usr/bin/env python3
"""Test MetaSOP UI integration by simulating a WebSocket message."""

import socketio
import asyncio
import json
import sys
import os
from typing import Any

# Add the OpenHands directory to the path
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
        print("Connected to OpenHands server")

    @sio.event
    async def disconnect():
        print("Disconnected from server")

    @sio.event
    async def oh_event(data):
        """Handle oh_event messages from the server."""
        print(f"Received oh_event: {data}")
        received_events.append(data)

        # Check for MetaSOP status updates
        if isinstance(data, dict):
            if data.get("status_update"):
                print(f"🎯 MetaSOP Status: {data.get('type', 'unknown')} - {data.get('message', 'no message')}")
            elif data.get("metasop_event"):
                metasop_event = data["metasop_event"]
                print(f"🎯 MetaSOP Event: {metasop_event.get('status', 'unknown')} - Step: {metasop_event.get('step_id', 'unknown')}")

    @sio.event
    async def connect_error(data):
        print(f"❌ Connection error: {data}")

    try:
        # Connect to the server with a test conversation ID
        conversation_id = "test-ui-metasop"
        await sio.connect(f'http://localhost:3000?conversation_id={conversation_id}')

        # Wait a moment for connection to establish
        await asyncio.sleep(1)

        # Send a MetaSOP message like the UI would
        message_data = {
            "action": "message",
            "args": {
                "content": "sop: Create a simple calculator with basic operations",
                "image_urls": [],
                "file_urls": [],
                "timestamp": "2025-01-05T12:30:00.000Z"
            }
        }

        print(f"Sending MetaSOP message: {message_data['args']['content']}")
        await sio.emit("oh_user_action", message_data)

        # Wait for MetaSOP responses
        print("Waiting for MetaSOP responses...")
        await asyncio.sleep(10)

        # Check what events we received
        print(f"\nSummary: Received {len(received_events)} events")

        metasop_events = [e for e in received_events if e.get("metasop_event")]
        status_events = [e for e in received_events if e.get("status_update")]

        print(f"MetaSOP Events: {len(metasop_events)}")
        print(f"Status Events: {len(status_events)}")

        if metasop_events or status_events:
            print("MetaSOP is working! Received MetaSOP-related events.")
        else:
            print("No MetaSOP events received. Check server logs for issues.")

        await sio.disconnect()
        print("Test completed")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_metasop_ui_message())
