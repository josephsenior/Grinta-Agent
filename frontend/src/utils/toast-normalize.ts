export function normalizeToastMessage(input: unknown): string {
  if (input == null) {
    return "";
  }
  if (typeof input === "string") {
    return input;
  }
  try {
    if (input && typeof input === "object" && "message" in input) {
      const rec = input as Record<string, unknown>;
      if (typeof rec.message === "string") return rec.message as string;
    }
  } catch (_) {
    // ignore
  }
  try {
    return String(input);
  } catch (_) {
    return "";
  }
}
