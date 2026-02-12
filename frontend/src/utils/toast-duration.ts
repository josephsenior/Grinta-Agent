import {
  TOAST_BUFFER_FACTOR,
  TOAST_CHARS_PER_WORD,
  TOAST_MAX_DURATION,
  TOAST_MIN_DURATION_ERROR,
  TOAST_MIN_DURATION_SUCCESS,
  TOAST_WORDS_PER_MINUTE,
} from "../constants/app";

/**
 * Calculate toast duration based on message length
 * @param message - The message to display
 * @param minDuration - Minimum duration in milliseconds (default: 5000 for success, 4000 for error)
 * @param maxDuration - Maximum duration in milliseconds (default: 10000)
 * @returns Duration in milliseconds
 */
export const calculateToastDuration = (
  message: string,
  minDuration: number = TOAST_MIN_DURATION_SUCCESS,
  maxDuration: number = TOAST_MAX_DURATION,
): number => {
  // Calculate duration based on reading speed (average 200 words per minute)
  // Assuming average word length of 5 characters
  const charactersPerMinute = TOAST_WORDS_PER_MINUTE * TOAST_CHARS_PER_WORD;
  const charactersPerSecond = charactersPerMinute / 60;

  // Calculate time needed to read the message
  const readingTimeMs = (message.length / charactersPerSecond) * 1000;

  // Add some buffer time (50% extra) for processing
  const durationWithBuffer = readingTimeMs * TOAST_BUFFER_FACTOR;

  // Ensure duration is within min/max bounds
  return Math.min(Math.max(durationWithBuffer, minDuration), maxDuration);
};
