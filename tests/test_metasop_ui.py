#!/usr/bin/env python3
"""Test MetaSOP functionality directly via WebSocket."""

import asyncio
import socketio
import json
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
        await sio.connect(f'http://localhost:3000?conversation_id={conversation_id}')
        print("Connected successfully")

        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)

        # Send a MetaSOP message
        message_data = {
            "action": "message",
            "args": {
                "content": "sop: Create a simple calculator function with add, subtract, multiply, and divide operations",
                "image_urls": [],
                "file_urls": [],
                "timestamp": "2025-01-04T22:30:00.000Z"
            }
        }

        print("Sending MetaSOP message...")
        await sio.emit("oh_user_action", message_data)

        # Wait for responses
        print("Waiting for MetaSOP responses...")
        await asyncio.sleep(15)

        # Send another message to trigger more events
        message_data2 = {
            "action": "message",
            "args": {
                "content": "sop: Create a simple hello world function",
                "image_urls": [],
                "file_urls": [],
                "timestamp": "2025-01-04T22:35:00.000Z"
            }
        }

        print("Sending second MetaSOP message...")
        await sio.emit("oh_user_action", message_data2)

        # Wait for more responses
        await asyncio.sleep(10)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await sio.disconnect()
        print("Test completed")

if __name__ == "__main__":
    asyncio.run(test_metasop_ui())
