"""WebSocket Server - Real-Time Communication.

Provides real-time communication between the optimization engine and clients
for live updates, monitoring, and control.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from forge.core.logger import forge_logger as logger
from forge.prompt_optimization.realtime.live_optimizer import LiveOptimizer
from forge.prompt_optimization.realtime.real_time_monitor import RealTimeMonitor


class WebSocketMessageType:
    """Types of WebSocket messages."""
    # Client to Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    GET_STATUS = "get_status"
    TRIGGER_OPTIMIZATION = "trigger_optimization"
    GET_METRICS = "get_metrics"
    GET_ALERTS = "get_alerts"
    CLEAR_ALERT = "clear_alert"
    
    # Server to Client
    STATUS_UPDATE = "status_update"
    METRICS_UPDATE = "metrics_update"
    ALERT_NOTIFICATION = "alert_notification"
    OPTIMIZATION_RESULT = "optimization_result"
    ERROR_MESSAGE = "error_message"
    HEARTBEAT = "heartbeat"


class WebSocketOptimizationServer:  # pragma: no cover - requires live websocket environment
    """WebSocket Server for real-time optimization communication.
    
    Features:
    - Real-time updates
    - Client subscription management
    - Live monitoring data
    - Remote control capabilities
    - Error handling and reconnection
    - Message queuing
    """

    def __init__(
        self,
        live_optimizer: LiveOptimizer,
        real_time_monitor: RealTimeMonitor,
        host: str = "localhost",
        port: int = 8765,
        heartbeat_interval: float = 30.0,
        max_clients: int = 100
    ):
        """Store dependencies and initialize connection tracking for WebSocket control plane."""
        self.live_optimizer = live_optimizer
        self.real_time_monitor = real_time_monitor
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.max_clients = max_clients
        
        # Server state
        self.server = None
        self.is_running = False
        self.clients: Set[WebSocketServerProtocol] = set()
        self.client_subscriptions: Dict[WebSocketServerProtocol, Set[str]] = {}
        
        # Message handling
        self.message_handlers = {
            WebSocketMessageType.SUBSCRIBE: self._handle_subscribe,
            WebSocketMessageType.UNSUBSCRIBE: self._handle_unsubscribe,
            WebSocketMessageType.GET_STATUS: self._handle_get_status,
            WebSocketMessageType.TRIGGER_OPTIMIZATION: self._handle_trigger_optimization,
            WebSocketMessageType.GET_METRICS: self._handle_get_metrics,
            WebSocketMessageType.GET_ALERTS: self._handle_get_alerts,
            WebSocketMessageType.CLEAR_ALERT: self._handle_clear_alert
        }
        
        # Background tasks
        self.heartbeat_task = None
        self.monitoring_task = None
        
        # Statistics
        self.server_stats = {
            'clients_connected': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'start_time': None
        }
        
        logger.info(f"WebSocket server initialized on {host}:{port}")

    async def start(self) -> None:  # pragma: no cover - requires active websocket server loop
        """Start the WebSocket server."""
        if self.is_running:
            logger.warning("WebSocket server is already running")
            return
        
        try:
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                max_size=1024 * 1024,  # 1MB max message size
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_running = True
            self.server_stats['start_time'] = datetime.now()
            
            # Start background tasks
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
            
            # Keep server running
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise

    async def stop(self) -> None:  # pragma: no cover - requires active websocket server loop
        """Stop the WebSocket server."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        # Close all client connections
        for client in list(self.clients):
            await self._close_client(client)
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("WebSocket server stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:  # pragma: no cover - requires live websocket client
        """Handle a new client connection."""
        if len(self.clients) >= self.max_clients:
            await websocket.close(code=1013, reason="Server at capacity")
            return
        
        self.clients.add(websocket)
        self.client_subscriptions[websocket] = set()
        self.server_stats['clients_connected'] = len(self.clients)
        
        client_address = websocket.remote_address
        logger.info(f"Client connected: {client_address}")
        
        try:
            # Send welcome message
            await self._send_message(websocket, {
                'type': 'welcome',
                'message': 'Connected to optimization server',
                'timestamp': datetime.now().isoformat()
            })
            
            # Handle messages from client
            async for message in websocket:
                await self._handle_message(websocket, message)
                
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_address}")
        except WebSocketException as e:
            logger.error(f"WebSocket error with client {client_address}: {e}")
            self.server_stats['errors'] += 1
        except Exception as e:
            logger.error(f"Unexpected error with client {client_address}: {e}")
            self.server_stats['errors'] += 1
        finally:
            await self._close_client(websocket)

    async def _close_client(self, websocket: WebSocketServerProtocol) -> None:
        """Close a client connection and clean up."""
        if websocket in self.clients:
            self.clients.remove(websocket)
            if websocket in self.client_subscriptions:
                del self.client_subscriptions[websocket]
            self.server_stats['clients_connected'] = len(self.clients)
            
            try:
                await websocket.close()
            except:
                pass

    async def _handle_message(self, websocket: WebSocketServerProtocol, message: str) -> None:
        """Handle a message from a client."""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](websocket, data)
            else:
                await self._send_error(websocket, f"Unknown message type: {message_type}")
            
            self.server_stats['messages_received'] += 1
            
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error(websocket, f"Message handling error: {str(e)}")

    async def _handle_subscribe(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle subscription request."""
        subscription_type = data.get('subscription_type')
        
        if not subscription_type:
            await self._send_error(websocket, "Missing subscription_type")
            return
        
        self.client_subscriptions[websocket].add(subscription_type)
        
        await self._send_message(websocket, {
            'type': 'subscription_confirmed',
            'subscription_type': subscription_type,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Client subscribed to {subscription_type}")

    async def _handle_unsubscribe(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle unsubscription request."""
        subscription_type = data.get('subscription_type')
        
        if not subscription_type:
            await self._send_error(websocket, "Missing subscription_type")
            return
        
        self.client_subscriptions[websocket].discard(subscription_type)
        
        await self._send_message(websocket, {
            'type': 'unsubscription_confirmed',
            'subscription_type': subscription_type,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Client unsubscribed from {subscription_type}")

    async def _handle_get_status(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle status request."""
        status = self.live_optimizer.get_optimization_status()
        
        await self._send_message(websocket, {
            'type': WebSocketMessageType.STATUS_UPDATE,
            'data': status,
            'timestamp': datetime.now().isoformat()
        })

    async def _handle_trigger_optimization(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle optimization trigger request."""
        prompt_id = data.get('prompt_id')
        priority = data.get('priority', 5)
        context = data.get('context', {})
        
        if not prompt_id:
            await self._send_error(websocket, "Missing prompt_id")
            return
        
        try:
            event_id = await self.live_optimizer.trigger_optimization(
                prompt_id=prompt_id,
                priority=priority,
                context=context
            )
            
            await self._send_message(websocket, {
                'type': 'optimization_triggered',
                'event_id': event_id,
                'prompt_id': prompt_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            await self._send_error(websocket, f"Failed to trigger optimization: {str(e)}")

    async def _handle_get_metrics(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle metrics request."""
        prompt_id = data.get('prompt_id')
        limit = data.get('limit', 100)
        
        metrics = self.real_time_monitor.get_current_metrics(prompt_id)
        
        await self._send_message(websocket, {
            'type': WebSocketMessageType.METRICS_UPDATE,
            'data': metrics,
            'timestamp': datetime.now().isoformat()
        })

    async def _handle_get_alerts(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle alerts request."""
        prompt_id = data.get('prompt_id')
        limit = data.get('limit', 100)
        
        alerts = self.real_time_monitor.get_active_alerts(prompt_id)
        alert_data = [asdict(alert) for alert in alerts]
        
        await self._send_message(websocket, {
            'type': WebSocketMessageType.ALERT_NOTIFICATION,
            'data': alert_data,
            'timestamp': datetime.now().isoformat()
        })

    async def _handle_clear_alert(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle alert clear request."""
        alert_id = data.get('alert_id')
        
        if not alert_id:
            await self._send_error(websocket, "Missing alert_id")
            return
        
        success = self.real_time_monitor.clear_alert(alert_id)
        
        await self._send_message(websocket, {
            'type': 'alert_cleared',
            'alert_id': alert_id,
            'success': success,
            'timestamp': datetime.now().isoformat()
        })

    async def _send_message(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]) -> None:
        """Send a message to a client."""
        try:
            await websocket.send(json.dumps(message, default=str))
            self.server_stats['messages_sent'] += 1
        except ConnectionClosed:
            await self._close_client(websocket)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def _send_error(self, websocket: WebSocketServerProtocol, error_message: str) -> None:
        """Send an error message to a client."""
        await self._send_message(websocket, {
            'type': WebSocketMessageType.ERROR_MESSAGE,
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        })

    async def _heartbeat_loop(self) -> None:  # pragma: no cover - long-running background task
        """Send heartbeat messages to all clients."""
        while self.is_running:
            try:
                heartbeat_message = {
                    'type': WebSocketMessageType.HEARTBEAT,
                    'timestamp': datetime.now().isoformat(),
                    'server_stats': self.server_stats
                }
                
                # Send to all connected clients
                for client in list(self.clients):
                    try:
                        await self._send_message(client, heartbeat_message)
                    except:
                        # Remove disconnected clients
                        await self._close_client(client)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(1.0)

    async def _monitoring_loop(self) -> None:  # pragma: no cover - long-running background task
        """Monitor for updates and broadcast to subscribed clients."""
        while self.is_running:
            try:
                # Get current metrics
                current_metrics = self.real_time_monitor.get_current_metrics()
                
                # Get active alerts
                active_alerts = self.real_time_monitor.get_active_alerts()
                
                # Broadcast to subscribed clients
                for client in list(self.clients):
                    subscriptions = self.client_subscriptions.get(client, set())
                    
                    # Send metrics update
                    if 'metrics' in subscriptions and current_metrics:
                        await self._send_message(client, {
                            'type': WebSocketMessageType.METRICS_UPDATE,
                            'data': current_metrics,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    # Send alerts
                    if 'alerts' in subscriptions and active_alerts:
                        alert_data = [asdict(alert) for alert in active_alerts]
                        await self._send_message(client, {
                            'type': WebSocketMessageType.ALERT_NOTIFICATION,
                            'data': alert_data,
                            'timestamp': datetime.now().isoformat()
                        })
                
                await asyncio.sleep(1.0)  # Update every second
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1.0)

    async def broadcast_message(self, message: Dict[str, Any], subscription_type: Optional[str] = None) -> None:  # pragma: no cover - network I/O
        """Broadcast a message to all clients or specific subscribers."""
        for client in list(self.clients):
            if subscription_type:
                subscriptions = self.client_subscriptions.get(client, set())
                if subscription_type not in subscriptions:
                    continue
            
            try:
                await self._send_message(client, message)
            except:
                await self._close_client(client)

    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            'is_running': self.is_running,
            'host': self.host,
            'port': self.port,
            'clients_connected': len(self.clients),
            'max_clients': self.max_clients,
            'heartbeat_interval': self.heartbeat_interval,
            'stats': self.server_stats.copy()
        }

    def get_client_info(self) -> List[Dict[str, Any]]:
        """Get information about connected clients."""
        client_info = []
        for client in self.clients:
            subscriptions = list(self.client_subscriptions.get(client, set()))
            client_info.append({
                'address': client.remote_address,
                'subscriptions': subscriptions,
                'connected_at': getattr(client, 'connected_at', None)
            })
        return client_info
