import { describe, it, expect } from "vitest";
import { parseArtifact } from "#/utils/artifact-parser";

describe("artifact-parser", () => {
  it("parses a simple product manager artifact and normalizes estimate", () => {
    const raw = {
      user_stories: [
        {
          id: "u1",
          title: "Story One",
          story: "Do something",
          estimate: 5,
          priority: "High",
        },
      ],
      success_metrics: [{ metric: "uptime", target: 99.9 }],
    };

    const parsed = parseArtifact(raw, "product_manager");
    expect(parsed.role).toBe("product_manager");
    const pm = parsed.data as any;
    expect(pm.user_stories?.length).toBe(1);
    expect(pm.user_stories[0].estimate).toBe("5");
    expect(pm.success_metrics?.[0].target).toBe("99.9");
  });

  it("parses an architect artifact and filters invalid api endpoints and components", () => {
    const raw = {
      api_endpoints: [
        { method: "POST", path: "/create" },
        { method: "INVALID", path: 123 },
      ],
      system_architecture: {
        components: [
          { id: "c1", name: "Auth", type: "api" },
          { name: "Broken" },
        ],
      },
      database_schema: [
        {
          table_name: "users",
          columns: [
            { name: "id", type: "string" },
            { name: 1, type: 2 },
          ],
        },
      ],
    };

    const parsed = parseArtifact(raw, "architect");
    expect(parsed.role).toBe("architect");
    const arch = parsed.data as any;
    expect(arch.api_endpoints?.length).toBe(1);
    expect(arch.api_endpoints?.[0].method).toBe("POST");
    expect(arch.system_architecture?.components?.length).toBe(1);
    expect(arch.database_schema?.[0].columns?.[0].name).toBe("id");
  });

  it("parses QA artifact and sanitizes test scenarios and security findings", () => {
    const raw = {
      test_scenarios: [
        { title: "Test A", steps: ["a", "b"], priority: "p1" },
        { not_a_scenario: true },
      ],
      security_findings: [
        { title: "Issue", severity: "HIGH", line: 42 },
        { title: null },
      ],
    };

    const parsed = parseArtifact(raw, "qa");
    expect(parsed.role).toBe("qa");
    const qa = parsed.data as any;
    expect(qa.test_scenarios?.length).toBe(1);
    expect(qa.test_scenarios?.[0].priority).toBe("high");
    expect(qa.security_findings?.length).toBe(1);
    expect(qa.security_findings?.[0].severity).toBe("high");
  });
});
