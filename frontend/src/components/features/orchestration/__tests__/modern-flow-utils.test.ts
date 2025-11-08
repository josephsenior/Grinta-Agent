import { describe, expect, it } from "vitest";
import {
  formatStepDateTime,
  formatStepTimestamp,
  getRoleMeta,
  getStatusMeta,
  normalizeProgress,
  normalizeRole,
  normalizeStatus,
} from "../modern-flow-utils";

describe("modern-flow-utils", () => {
  describe("getStatusMeta", () => {
    it("normalizes common status aliases", () => {
      const runningMeta = getStatusMeta("running");
      expect(runningMeta.id).toBe("in_progress");
      expect(runningMeta.isInProgress).toBe(true);

      const doneMeta = getStatusMeta("completed");
      expect(doneMeta.id).toBe("complete");
      expect(doneMeta.isComplete).toBe(true);

      const failedMeta = getStatusMeta("error");
      expect(failedMeta.id).toBe("blocked");
      expect(failedMeta.isBlocked).toBe(true);
    });

    it("falls back to unknown for unsupported statuses", () => {
      const meta = getStatusMeta(123);
      expect(meta.id).toBe("unknown");
      expect(meta.label).toBe("Unknown");
    });
  });

  describe("getRoleMeta", () => {
    it("returns labels and icons for known roles", () => {
      const architect = getRoleMeta("architect");
      expect(architect.id).toBe("architect");
      expect(architect.label).toBe("Architect");

      const engineer = getRoleMeta("Platform Engineer");
      expect(engineer.id).toBe("engineer");
      expect(engineer.label).toBe("Engineer");
    });

    it("defaults to other for unknown roles", () => {
      const meta = getRoleMeta("data_scientist");
      expect(meta.id).toBe("other");
      expect(meta.label).toBe("Agent");
    });
  });

  describe("normalizeProgress", () => {
    it("clamps values into the 0-100 range", () => {
      expect(normalizeProgress(120)).toBe(100);
      expect(normalizeProgress(-5)).toBe(0);
      expect(normalizeProgress(42.2)).toBe(42);
    });

    it("ignores non-numeric values", () => {
      expect(normalizeProgress("50")).toBeUndefined();
    });
  });

  describe("formatStepTimestamp/date", () => {
    it("returns undefined for falsy or invalid values", () => {
      expect(formatStepTimestamp(undefined)).toBeUndefined();
      expect(formatStepDateTime("not-a-date")).toBeUndefined();
    });

    it("formats valid date inputs", () => {
      const iso = "2024-01-01T12:00:00.000Z";
      expect(formatStepTimestamp(iso)).toBeTruthy();
      expect(formatStepDateTime(new Date(iso))).toBeTruthy();
    });
  });

  describe("normalizers", () => {
    it("normalizes status strings", () => {
      expect(normalizeStatus("In Progress")).toBe("in_progress");
      expect(normalizeStatus("FAILED")).toBe("blocked");
    });

    it("normalizes role strings", () => {
      expect(normalizeRole("Product-Manager")).toBe("product_manager");
      expect(normalizeRole("QA Specialist")).toBe("qa");
    });
  });
});


