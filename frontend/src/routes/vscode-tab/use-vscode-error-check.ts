export function hasVSCodeError(
  error: unknown,
  dataError: string | undefined,
  url: string | undefined,
  iframeError: string | null,
): boolean {
  return Boolean(error || dataError || !url || iframeError);
}
