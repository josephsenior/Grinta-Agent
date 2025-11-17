#!/usr/bin/env python3
"""Test MetaSOP functionality directly via WebSocket."""

import asyncio
import json
import socketio
import uuid


async def test_metasop_ui():
    """Test MetaSOP by sending a message via WebSocket."""
    print("Testing MetaSOP via WebSocket...")

    # Create Socket.IO client
    sio = socketio.AsyncClient()

    conversation_id = str(uuid.uuid4())
    print(f"Using conversation ID: {conversation_id}")

    @sio.event
    async def connect():
        """Report WebSocket connection success for MetaSOP UI test."""
        print("Connected to WebSocket!")

    @sio.event
    async def disconnect():
        """Report WebSocket disconnect for MetaSOP UI test."""
        print("Disconnected from WebSocket")

    @sio.event
    async def oh_event(data):
        """Echo received MetaSOP events during the test run."""
        print(f"Received event: {data}")

    try:
        # Connect to the server with conversation_id
        await sio.connect(f"http://localhost:3000?conversation_id={conversation_id}")
        print("Connected successfully")

        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)

        # Send a test message
        message = {
            "action": "message",
            "args": {
                "content": "sop: Create a simple todo list app with React",
                "image_urls": [],
                "file_urls": [],
                "timestamp": "2025-01-04T22:05:00.000Z",
            },
        }

        print("Sending message...")
        print(json.dumps(message, indent=2))
        await sio.emit("oh_user_action", message)

        # Wait for responses
        await asyncio.sleep(5)

        print("Test complete")
    except Exception as e:
        print(f"Error during WebSocket test: {e}")
    finally:
        await sio.disconnect()


if __name__ == "__main__":
    asyncio.run(test_metasop_ui())
