# API Documentation

Forge provides comprehensive APIs for integrating with the platform programmatically.

## REST API

The REST API provides HTTP endpoints for all platform features:

- **Authentication**: JWT-based authentication and session management
- **Agent Operations**: Run CodeAct agent and MetaSOP orchestrator
- **Memory Management**: Store and retrieve conversation history
- **Optimization**: Real-time prompt optimization and performance monitoring
- **Tools**: Execute various tools and get available tool listings
- **Monitoring**: System health checks and metrics

[View REST API Reference](api/rest-api.md)

## WebSocket API

Real-time communication via WebSocket for live updates:

- **Agent Events**: Live agent responses and status updates
- **MetaSOP Events**: Orchestration progress and visualization data
- **Optimization Events**: Real-time optimization updates
- **Memory Events**: Conversation storage notifications

[View WebSocket API Reference](api/websocket-api.md)

## SDKs

### Python SDK

Programmatic access to Forge from Python applications.

[View Python SDK Documentation](api/python-sdk.md)

### TypeScript SDK

TypeScript/JavaScript SDK for frontend and Node.js applications.

[View TypeScript SDK Documentation](api/typescript-sdk.md)

## Authentication

All APIs support multiple authentication methods:

- **JWT Tokens**: Bearer token authentication
- **API Keys**: Service-to-service authentication
- **Session Cookies**: Web client authentication

## Rate Limiting

API requests are rate-limited to ensure fair usage:

- **REST API**: 100 requests per minute per user
- **WebSocket**: 1000 messages per minute per connection

## Error Handling

Consistent error response format across all APIs with detailed error codes and messages.

## Examples

Complete code examples for common integration patterns:

- Agent execution workflows
- Memory management
- Real-time event handling
- Authentication flows