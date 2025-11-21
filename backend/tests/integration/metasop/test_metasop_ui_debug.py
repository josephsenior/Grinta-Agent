#!/usr/bin/env python3
"""Test MetaSOP UI message handling with detailed logging."""

import asyncio
import json
import socketio
import time


async def test_metasop_with_logging():
    """Test MetaSOP message handling with detailed logging."""
    print("=== Testing MetaSOP UI Message Handling ===")
    sio = socketio.AsyncClient()

    events_received = []

    @sio.event
    async def connect():
        """Log successful MetaSOP UI debug connection."""
        print("✅ Socket.IO connected!")

    @sio.event
    async def disconnect():
        """Log MetaSOP UI debug disconnection."""
        print("❌ Socket.IO disconnected")

    @sio.event
    async def connect_error(error):
        """Record any connection errors encountered during debug."""
        print(f"❌ Connection error: {error}")

    @sio.event
    async def oh_event(data):
        """Capture incoming oh_event payloads for debugging."""
        print(f"📥 Received oh_event: {json.dumps(data, indent=2)}")
        events_received.append(data)

    @sio.event
    async def message(data):
        """Capture inbound message events for debug logging."""
        print(f"📥 Received message: {json.dumps(data, indent=2)}")

    try:
        await sio.connect("http://localhost:3000")
        print("✅ Connected successfully")

        payload = {
            "action": "message",
            "args": {
                "content": "sop: Provide a debugging checklist for WebSocket issues",
                "image_urls": [],
                "file_urls": [],
                "timestamp": "2025-01-04T22:05:00.000Z",
            },
        }

        print("\n📤 Sending debug MetaSOP message...")
        print(json.dumps(payload, indent=2))
        await sio.emit("oh_user_action", payload)

        print("\n⏳ Waiting for responses...")
        start = time.time()
        while time.time() - start < 10:
            await asyncio.sleep(0.5)
            if events_received:
                print(f"📊 Events so far: {len(events_received)}")

        print("\nSummary of events received:")
        for idx, event in enumerate(events_received, 1):
            print(f"{idx}. {json.dumps(event, indent=2)}")

    except Exception as exc:
        print(f"❌ Debug test error: {exc}")
    finally:
        await sio.disconnect()


if __name__ == "__main__":
    asyncio.run(test_metasop_with_logging())
