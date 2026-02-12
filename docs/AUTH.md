# Forge session authentication (OSS)

Forge OSS uses a single shared **session API key** to authenticate both HTTP requests and Socket.IO connections.

This document is the single source of truth for:
- Which credentials are accepted
- Where they must be sent (headers vs WebSocket handshake)
- When (and how) query-string token auth is allowed

## Source of the session key

The backend resolves the expected key in this priority order:
1. `SESSION_API_KEY` environment variable
2. A persisted key in `.env.local` (created by a prior run)
3. Auto-generated key (written to `.env.local` when possible)

If the resolved key is non-empty, auth is enforced for protected routes.

## HTTP (REST) auth invariants

Preferred:
- Send `X-Session-API-Key: <SESSION_API_KEY>` on every request.

Also accepted:
- `Authorization: Bearer <SESSION_API_KEY>`

Opt-in (disabled by default; leak-prone):
- If `FORGE_ALLOW_QUERY_TOKEN_AUTH=true`, the backend will also accept a token in the query string:
  - `?token=<SESSION_API_KEY>` or `?apiKey=<SESSION_API_KEY>`

Notes:
- Query-string tokens are discouraged because URLs often end up in logs, browser history, proxies, analytics, and referrers.

## Socket.IO auth invariants

Preferred:
- Provide the key in the Socket.IO **handshake auth payload**:
  - `auth: { session_api_key: "<SESSION_API_KEY>" }`

Opt-in (disabled by default; leak-prone):
- If `FORGE_ALLOW_QUERY_TOKEN_AUTH=true`, the backend will also accept `session_api_key` via the Socket.IO connection query string for legacy clients.

## Frontend expectations

The frontend stores a per-conversation `session_api_key` value (returned by the backend) and:
- Injects it into HTTP via `X-Session-API-Key`
- Sends it for Socket.IO via `auth.session_api_key`

## Troubleshooting

- 401s on HTTP: ensure the request includes `X-Session-API-Key` matching the backend’s resolved `SESSION_API_KEY`.
- Socket.IO connect errors (`invalid_session_api_key`): ensure the client passes `auth.session_api_key`.
- Only enable `FORGE_ALLOW_QUERY_TOKEN_AUTH` for local/dev compatibility, and never for shared deployments.
