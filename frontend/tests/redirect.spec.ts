import { expect, test } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

// Increase timeout for these E2E tests which may wait for MSW/socket startup
test.setTimeout(120000);

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("should redirect to /conversations after uploading a project zip", async ({
  page,
}) => {
  const filePath = path.join(dirname, "fixtures/project.zip");

  // The landing page renders a CTA which opens the project upload UI.
  // Click the primary CTA to reveal the file input if present.
  try {
    const startBtn = page.getByRole("button", { name: /start building/i });
    await startBtn.waitFor({ state: "visible", timeout: 60000 });
    try {
      await startBtn.click();
    } catch (err) {
      // fallback to DOM click if Playwright's click is intercepted
      await page.evaluate(() => {
        const btn = Array.from(document.querySelectorAll("button")).find((b) =>
          /start building/i.test(b.textContent || ""),
        ) as HTMLElement | undefined;
        if (btn) {
          btn.click();
        }
      });
    }
  } catch (err) {
    // If the CTA cannot be found, continue — the input might be present directly
  }

  // Wait for the native file input element to be visible and use an
  // element handle `setInputFiles` which can be more reliable than a
  // labeled locator in some Vite/react render timing races.
  try {
    const inputHandle = await page.waitForSelector("input[type=file]", {
      state: "visible",
      timeout: 90000,
    });
    // elementHandle.setInputFiles accepts the same arguments as locator.setInputFiles
    await inputHandle.setInputFiles(filePath);
  } catch (err) {
    // fallback: warn and no-op; tests may still fail but we'll get clearer traces
    console.warn(
      "setInputFiles failed; file input was not visible or could not accept files",
    );
  }

  await expect(page).toHaveURL(/\/conversations\/\d+/);
});

test("should redirect to /conversations after selecting a repo", async ({
  page,
}) => {
  // enter a github token to view the repositories
  const connectToGitHubButton = page.getByRole("button", {
    name: /connect to github/i,
  });
  await connectToGitHubButton.waitFor({ state: "visible", timeout: 60000 });
  try {
    await connectToGitHubButton.click();
  } catch (err) {
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll("button")).find((b) =>
        /connect to github/i.test(b.textContent || ""),
      ) as HTMLElement | undefined;
      if (btn) {
        btn.click();
      }
    });
  }
  const tokenInput = page.getByLabel(/github token\*/i);
  await tokenInput.fill("fake-token");

  const submitButton = page.getByTestId("connect-to-github");
  await submitButton.click();

  // select a repository
  const repoDropdown = page.getByLabel(/github repository/i);
  await repoDropdown.click();

  const repoItem = page.getByTestId("github-repo-item").first();
  await repoItem.click();

  // Wait for the conversations API to respond which indicates navigation completed
  await page.waitForResponse(
    (resp) =>
      /\/api\/conversations\/.+/.test(resp.url()) && resp.status() === 200,
    { timeout: 90000 },
  );
  await expect(page).toHaveURL(/\/conversations\/\d+/, { timeout: 60000 });
});

// FIXME: This fails because the MSW WS mocks change state too quickly,
// missing the OPENING status where the initial query is rendered.
test.skip("should redirect the user to /conversation with their initial query after selecting a project", async ({
  page,
}) => {
  // enter query
  const testQuery = "this is my test query";
  const textbox = page.getByPlaceholder(/what do you want to build/i);
  expect(textbox).not.toBeNull();
  await textbox.fill(testQuery);

  const fileInput = page.getByLabel("Upload a .zip");
  const filePath = path.join(dirname, "fixtures/project.zip");
  await fileInput.setInputFiles(filePath);

  await page.waitForURL("/conversation");

  // get user message
  const userMessage = page.getByTestId("user-message");
  expect(await userMessage.textContent()).toBe(testQuery);
});
