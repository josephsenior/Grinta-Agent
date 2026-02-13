/**
 * Centralized event normalization layer.
 *
 * Every raw object arriving from the Socket.IO `forge_event` channel
 * passes through {@link normalizeForgeEvent} **once** before being
 * stored in React state.  This single gateway ensures:
 *
 * - `id` is always a `number` (coerced from string if needed)
 * - `timestamp` is always a valid ISO-8601 string (defaults to now)
 * - `source` is always one of the known source types
 * - `message` is always a string (defaults to "")
 * - Missing `args` / `extras` objects get a safe empty default
 * - Literal `"NULL"` strings in payloads are replaced with `""`
 *
 * Downstream code can rely on these invariants instead of
 * duck-typing every access.
 */

// ------------------------------------------------------------------ //
// Constants
// ------------------------------------------------------------------ //

const VALID_SOURCES = new Set(["agent", "user", "environment"]);

// ------------------------------------------------------------------ //
// Helpers
// ------------------------------------------------------------------ //

/** Recursively replace literal `"NULL"` string values with `""`. */
function sanitizeNullStrings<T>(value: T): T {
  if (typeof value === "string") {
    return (value.toUpperCase() === "NULL" ? "" : value) as unknown as T;
  }
  if (Array.isArray(value)) {
    return value.map(sanitizeNullStrings) as unknown as T;
  }
  if (value !== null && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      out[k] = sanitizeNullStrings(v);
    }
    return out as T;
  }
  return value;
}

function coerceId(raw: unknown): number {
  if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  if (typeof raw === "string") {
    const n = Number(raw);
    if (Number.isFinite(n)) return n;
  }
  return -1;
}

function coerceTimestamp(raw: unknown): string {
  if (typeof raw === "string" && raw.length > 0) return raw;
  return new Date().toISOString();
}

function coerceSource(raw: unknown): "agent" | "user" | "environment" {
  if (typeof raw === "string" && VALID_SOURCES.has(raw)) {
    return raw as "agent" | "user" | "environment";
  }
  return "environment";
}

// ------------------------------------------------------------------ //
// Public API
// ------------------------------------------------------------------ //

export interface NormalizedEvent {
  /** Guaranteed numeric event ID. */
  id: number;
  /** Guaranteed valid ISO-8601 timestamp. */
  timestamp: string;
  /** Guaranteed known source type. */
  source: "agent" | "user" | "environment";
  /** Guaranteed string message (may be empty). */
  message: string;
  /** All other fields from the original event, sanitized. */
  [key: string]: unknown;
}

/**
 * Normalize a raw Socket.IO event into a shape with guaranteed
 * invariants.
 *
 * This is a **pure function** — it never mutates the input.
 */
export function normalizeForgeEvent(
  raw: Record<string, unknown>,
): NormalizedEvent {
  const sanitized = sanitizeNullStrings(raw);

  const id = coerceId(sanitized.id);
  const timestamp = coerceTimestamp(sanitized.timestamp);
  const source = coerceSource(sanitized.source);
  const message =
    typeof sanitized.message === "string" ? sanitized.message : "";

  // Ensure args/extras are always objects when present
  const args =
    sanitized.args && typeof sanitized.args === "object"
      ? sanitized.args
      : sanitized.action !== undefined
        ? {}
        : undefined;

  const extras =
    sanitized.extras && typeof sanitized.extras === "object"
      ? sanitized.extras
      : sanitized.observation !== undefined
        ? {}
        : undefined;

  const result: NormalizedEvent = {
    ...sanitized,
    id,
    timestamp,
    source,
    message,
  };

  if (args !== undefined) result.args = args;
  if (extras !== undefined) result.extras = extras;

  return result;
}

/**
 * Compact streaming chunks in an event list: replace consecutive
 * `streaming_chunk` actions from the same source with only the
 * **last** (which carries the full `accumulated` text).
 *
 * This dramatically reduces memory for long-running sessions where
 * hundreds of streaming deltas were stored individually.
 *
 * @param events  Parsed event array (not mutated)
 * @returns A new array with intermediate streaming chunks removed
 */
export function compactStreamingChunks<
  T extends { action?: string; source?: string; args?: Record<string, unknown> },
>(events: readonly T[]): T[] {
  if (events.length === 0) return [];

  const result: T[] = [];
  let i = 0;

  while (i < events.length) {
    const ev = events[i]!;

    if (ev.action !== "streaming_chunk") {
      result.push(ev);
      i++;
      continue;
    }

    // Scan forward to find the last consecutive streaming_chunk
    // from the same source.
    let lastChunkIdx = i;
    for (let j = i + 1; j < events.length; j++) {
      const next = events[j]!;
      if (next.action === "streaming_chunk" && next.source === ev.source) {
        lastChunkIdx = j;
      } else {
        break;
      }
    }

    // Keep only the final chunk (it contains the full accumulated text)
    result.push(events[lastChunkIdx]!);
    i = lastChunkIdx + 1;
  }

  return result;
}
