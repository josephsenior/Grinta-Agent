export function isPrimitiveError(
  error: unknown,
): error is string | number | boolean {
  return (
    typeof error === "string" ||
    typeof error === "number" ||
    typeof error === "boolean"
  );
}

export function isNullishError(error: unknown): error is null | undefined {
  return error === null || typeof error === "undefined";
}
