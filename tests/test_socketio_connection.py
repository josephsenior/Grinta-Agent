#!/usr/bin/env python3
"""Test script to diagnose Socket.IO connection issues."""
import socketio
import asyncio


async def test_socketio_connection():
    """Test Socket.IO connection with various configurations."""
    # Test 1: Basic connection
    print("=== Test 1: Basic Socket.IO Connection ===")
    sio = socketio.AsyncClient()

    @sio.event
    async def connect():
        """Log successful connection for basic Socket.IO scenario."""
        print("✅ Connected successfully!")

    @sio.event
    async def disconnect():
        """Log disconnect notification for basic scenario."""
        print("❌ Disconnected")

    try:
        await sio.connect('http://localhost:3000')
        await asyncio.sleep(2)
        await sio.disconnect()
        print("✅ Test 1 passed")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")

    # Test 2: Connection with conversation_id
    print("\n=== Test 2: Connection with conversation_id ===")
    sio2 = socketio.AsyncClient()

    @sio2.event
    async def connect():
        """Report connection success when passing conversation_id."""
        print("✅ Connected with conversation_id!")

    @sio2.event
    async def disconnect():
        """Report disconnect for conversation_id scenario."""
        print("❌ Disconnected")

    try:
        await sio2.connect('http://localhost:3000?conversation_id=test-conversation-123')
        await asyncio.sleep(2)
        await sio2.disconnect()
        print("✅ Test 2 passed")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")

    # Test 3: Connection with transport specification
    print("\n=== Test 3: Connection with transport specification ===")
    sio3 = socketio.AsyncClient()

    @sio3.event
    async def connect():
        """Report connection success when specifying transports."""
        print("✅ Connected with transport specification!")

    @sio3.event
    async def disconnect():
        """Report disconnect after transport test."""
        print("❌ Disconnected")

    try:
        await sio3.connect('http://localhost:3000',
                           transports=['websocket', 'polling'])
        await asyncio.sleep(2)
        await sio3.disconnect()
        print("✅ Test 3 passed")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")

    # Test 4: Check what happens with default namespace
    print("\n=== Test 4: Default namespace test ===")
    sio4 = socketio.AsyncClient()

    @sio4.event
    async def connect():
        """Report default-namespace connection success."""
        print("✅ Connected to default namespace!")

    @sio4.event
    async def disconnect():
        """Report default-namespace disconnect."""
        print("❌ Disconnected from default namespace")

    @sio4.event
    async def connect_error(data):
        """Log connection error payload for default namespace."""
        print(f"❌ Default namespace connection error: {data}")

    try:
        await sio4.connect('http://localhost:3000?conversation_id=test-default-namespace')
        await asyncio.sleep(2)
        await sio4.disconnect()
        print("✅ Test 4 passed")
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_socketio_connection())
