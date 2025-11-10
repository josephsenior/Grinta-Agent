#!/usr/bin/env python3
"""Test MetaSOP with a fresh conversation ID."""
import socketio
import asyncio
import json
import time
import uuid


async def test_metasop_fresh_conversation():
    """Test MetaSOP with a fresh conversation ID."""
    print("=== Testing MetaSOP with Fresh Conversation ===")
    sio = socketio.AsyncClient()

    events_received = []

    @sio.event
    async def connect():
        """Report successful connection for fresh conversation test."""
        print("✅ Socket.IO connected!")

    @sio.event
    async def disconnect():
        """Report disconnection for fresh conversation test."""
        print("❌ Socket.IO disconnected")

    @sio.event
    async def connect_error(error):
        """Log connection errors encountered during fresh conversation test."""
        print(f"❌ Connection error: {error}")

    @sio.event
    async def oh_event(data):
        """Capture oh_event payloads while exercising fresh conversation flow."""
        print(f"📥 Received oh_event: {json.dumps(data, indent=2)}")
        events_received.append(data)

    try:
        # Use a fresh conversation ID
        conversation_id = str(uuid.uuid4()).replace('-', '')[:32]
        print(f"Using conversation ID: {conversation_id}")

        await sio.connect(f'http://localhost:3000?conversation_id={conversation_id}')

        print("✅ Connected successfully")

        # Send MetaSOP message
        message_data = {
            'action': 'message',
            'args': {
                'content': 'sop: Create a simple calculator with basic operations',
                'image_urls': [],
                'file_urls': [],
                'timestamp': '2025-01-04T22:05:00.000Z'
            }
        }

        print("📤 Sending MetaSOP message...")
        print(f"Message data: {json.dumps(message_data, indent=2)}")

        await sio.emit('oh_user_action', message_data)

        # Wait for responses with timeout
        print("⏳ Waiting for responses...")
        start_time = time.time()
        while time.time() - start_time < 15:  # 15 second timeout
            await asyncio.sleep(0.5)
            if events_received:
                print(f"📊 Total events received: {len(events_received)}")

        print("✅ MetaSOP message sent successfully")

        # Summary
        print(f"\n📊 Summary:")
        print(f"- Events received: {len(events_received)}")
        for i, event in enumerate(events_received):
            event_type = event.get('type', 'unknown')
            message = event.get('message', str(event))[:100]
            print(f"  {i +1}. {event_type}: {message}")

        # Check for MetaSOP orchestration messages
        metasop_messages = [e for e in events_received if 'MetaSOP' in str(e)]
        if metasop_messages:
            print(f"\n🎉 Found {len(metasop_messages)} MetaSOP messages!")
            for msg in metasop_messages:
                print(f"   MetaSOP: {msg}")
        else:
            print(f"\n❌ No MetaSOP orchestration messages found")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(test_metasop_fresh_conversation())
