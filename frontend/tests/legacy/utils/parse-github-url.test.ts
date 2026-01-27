import { expect, test } from "vitest";
import { parseGithubUrl } from "#/utils/parse-github-url";

test("parseGithubUrl", () => {
  expect(
    parseGithubUrl("https://github.com/alexreardon/tiny-invariant"),
  ).toEqual(["alexreardon", "tiny-invariant"]);

  expect(parseGithubUrl("https://github.com/Forge/Forge")).toEqual([
    "Forge",
    "Forge",
  ]);

  expect(parseGithubUrl("https://github.com/Forge/")).toEqual([
    "Forge",
    "",
  ]);

  expect(parseGithubUrl("https://github.com/")).toEqual([]);
});


