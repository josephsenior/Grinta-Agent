/**
 * Hook for password strength calculation
 */
export function usePasswordStrength() {
  const getPasswordStrength = (
    password: string,
  ): { strength: "weak" | "medium" | "strong"; score: number } => {
    let score = 0;
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^a-zA-Z0-9]/.test(password)) score += 1;

    if (score <= 2) return { strength: "weak", score };
    if (score <= 4) return { strength: "medium", score };
    return { strength: "strong", score };
  };

  return { getPasswordStrength };
}
