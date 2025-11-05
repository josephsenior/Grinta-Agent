/**
 * Haptic Feedback Utility
 * 
 * Provides tactile feedback for user interactions on supported devices.
 * Falls back gracefully on devices without haptic support.
 */

type HapticStyle = "light" | "medium" | "heavy" | "selection" | "success" | "warning" | "error";

/**
 * Trigger haptic feedback
 * @param style - The intensity/type of haptic feedback
 */
export function triggerHaptic(style: HapticStyle = "light"): void {
  // Check if device supports Vibration API
  if (!("vibrate" in navigator)) {
    return; // Silently fail on unsupported devices
  }

  try {
    // Map styles to vibration patterns (in milliseconds)
    const patterns: Record<HapticStyle, number | number[]> = {
      light: 10,
      medium: 20,
      heavy: 30,
      selection: [5, 5],
      success: [10, 50, 10],
      warning: [20, 50, 20],
      error: [30, 100, 30, 100, 30],
    };

    const pattern = patterns[style] || 10;
    navigator.vibrate(pattern);
  } catch (error) {
    // Silently fail if vibration API throws
    console.debug("Haptic feedback not available:", error);
  }
}

/**
 * Higher-order function to add haptic feedback to click handlers
 * @param handler - Original click handler
 * @param hapticStyle - Type of haptic feedback
 * @returns Enhanced click handler with haptic feedback
 */
export function withHaptic<T extends (...args: any[]) => any>(
  handler: T,
  hapticStyle: HapticStyle = "light",
): T {
  return ((...args: any[]) => {
    triggerHaptic(hapticStyle);
    return handler(...args);
  }) as T;
}

/**
 * React hook for haptic feedback
 * @returns Object with haptic trigger functions
 */
export function useHaptic() {
  return {
    light: () => triggerHaptic("light"),
    medium: () => triggerHaptic("medium"),
    heavy: () => triggerHaptic("heavy"),
    selection: () => triggerHaptic("selection"),
    success: () => triggerHaptic("success"),
    warning: () => triggerHaptic("warning"),
    error: () => triggerHaptic("error"),
    trigger: triggerHaptic,
  };
}

/**
 * Check if device supports haptic feedback
 * @returns true if haptic feedback is available
 */
export function isHapticSupported(): boolean {
  return "vibrate" in navigator;
}

