# Auth invariants (backend + frontend)

This repo uses a **single session API key** model for Forge OSS.

## Environment

- `SESSION_API_KEY` (server-side): the expected secret.
- `FORGE_ALLOW_QUERY_TOKEN_AUTH` (server-side, default `false`): **opt-in** support for legacy query-param token auth.

## HTTP (REST) authentication

Accepted client auth mechanisms:

1. Preferred: `X-Session-API-Key: <SESSION_API_KEY>`
2. Also accepted: `Authorization: Bearer <SESSION_API_KEY>`

Query token auth:

- **Disabled by default.**
- If `FORGE_ALLOW_QUERY_TOKEN_AUTH=true`, the server may accept `?session_api_key=<SESSION_API_KEY>` on some endpoints for backwards compatibility.
- Do not rely on query tokens in new code. They are easier to leak via logs, caches, referers, and tooling.

## Socket.IO authentication

Preferred:

- Send the key via Socket.IO handshake auth:

  - `auth: { "session_api_key": "<SESSION_API_KEY>" }`

Legacy:

- Query-param auth (e.g. `?session_api_key=...`) is **rejected by default**.
- If `FORGE_ALLOW_QUERY_TOKEN_AUTH=true`, the server may allow query-param auth for legacy clients.

## Frontend expectations

- HTTP requests should always include `X-Session-API-Key` when the current conversation has `session_api_key`.
- Websocket connections should send `session_api_key` in the Socket.IO handshake `auth` payload.

## Threat model notes

- Treat the session API key like a password.
- Prefer headers / handshake auth over query params to reduce accidental disclosure.
