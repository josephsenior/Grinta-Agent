import { describe, it, expect, vi, beforeEach } from "vitest";
import safeToast from "#/utils/safe-hot-toast";
import {
  displaySuccessToast,
  displayErrorToast,
} from "#/utils/custom-toast-handlers";

// Mock our safe wrapper so tests don't call the real library
vi.mock("#/utils/safe-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    show: vi.fn(),
  },
}));

describe("custom-toast-handlers", () => {
  type MockFn = ReturnType<typeof vi.fn>;

  const toastMock = safeToast as unknown as {
    success: MockFn;
    error: MockFn;
    show: MockFn;
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("displaySuccessToast", () => {
    it("should call toast.success with calculated duration for short message", () => {
      const shortMessage = "Settings saved";
      displaySuccessToast(shortMessage);

      expect(toastMock.success).toHaveBeenCalledWith(
        shortMessage,
        expect.objectContaining({
          duration: 5000, // Should use minimum duration of 5000ms
          position: "top-right",
          style: expect.any(Object),
        }),
      );
    });

    it("should call toast.success with longer duration for long message", () => {
      const longMessage =
        "Settings saved. For old conversations, you will need to stop and restart the conversation to see the changes.";
      displaySuccessToast(longMessage);

      expect(toastMock.success).toHaveBeenCalledWith(
        longMessage,
        expect.objectContaining({
          duration: expect.any(Number),
          position: "top-right",
          style: expect.any(Object),
        }),
      );

      // Get the actual duration that was passed
      const callArgs = (
        toastMock.success as unknown as { mock: { calls: unknown[][] } }
      ).mock.calls[0][1] as { duration: number };
      const actualDuration = callArgs.duration;

      // For a long message, duration should be more than the minimum 5000ms
      expect(actualDuration).toBeGreaterThan(5000);
      // But should not exceed the maximum 10000ms
      expect(actualDuration).toBeLessThanOrEqual(10000);
    });
  });

  describe("displayErrorToast", () => {
    it("should call toast.error with calculated duration for short message", () => {
      const shortMessage = "Error occurred";
      displayErrorToast(shortMessage);

      expect(toastMock.error).toHaveBeenCalledWith(
        shortMessage,
        expect.objectContaining({
          duration: 4000, // Should use minimum duration of 4000ms for errors
          position: "top-right",
          style: expect.any(Object),
        }),
      );
    });

    it("should call toast.error with longer duration for long error message", () => {
      const longMessage =
        "A very long error message that should take more time to read and understand what went wrong with the operation.";
      displayErrorToast(longMessage);

      expect(toastMock.error).toHaveBeenCalledWith(
        longMessage,
        expect.objectContaining({
          duration: expect.any(Number),
          position: "top-right",
          style: expect.any(Object),
        }),
      );

      // Get the actual duration that was passed
      const callArgs = (
        toastMock.error as unknown as {
          mock: { calls: unknown[][] };
        }
      ).mock.calls[0][1] as { duration: number };
      const actualDuration = callArgs.duration;

      // For a long message, duration should be more than the minimum 4000ms
      expect(actualDuration).toBeGreaterThan(4000);
      // But should not exceed the maximum 10000ms
      expect(actualDuration).toBeLessThanOrEqual(10000);
    });
  });
});
