#!/usr/bin/env python3
"""Test MetaSOP UI message handling with detailed logging."""
import socketio
import asyncio
import json
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
        events_received.append(data)

    @sio.event
    async def status_update(data):
        """Capture status updates emitted during debug session."""
        print(f"📥 Received status_update: {json.dumps(data, indent=2)}")
        events_received.append(data)

    try:
        # Connect with conversation_id
        conversation_id = '26384b3861d146e898e52ffc3db18243'
        await sio.connect(f'http://localhost:3000?conversation_id={conversation_id}')

        print("✅ Connected successfully")

        # Send MetaSOP message exactly as the UI would
        message_data = {
            'action': 'message',
            'args': {
                'content': 'sop: Create a simple test function',
                'image_urls': [],
                'file_urls': [],
                'timestamp': '2025-01-04T22:00:00.000Z'
            }
        }

        print("📤 Sending MetaSOP message...")
        print(f"Message data: {json.dumps(message_data, indent=2)}")

        await sio.emit('oh_user_action', message_data)

        # Wait for responses with timeout
        print("⏳ Waiting for responses...")
        start_time = time.time()
        while time.time() - start_time < 10:  # 10 second timeout
            await asyncio.sleep(0.5)
            if events_received:
                print(f"📊 Total events received: {len(events_received)}")

        print("✅ MetaSOP message sent successfully")

        # Summary
        print(f"\n📊 Summary:")
        print(f"- Events received: {len(events_received)}")
        for i, event in enumerate(events_received):
            print(f"  {i +1}. {event.get('type', 'unknown')}: {event.get('message', str(event))[:100]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(test_metasop_with_logging())
