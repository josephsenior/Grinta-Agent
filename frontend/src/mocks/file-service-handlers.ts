import { delay, http, HttpResponse } from "msw";

export const FILE_VARIANTS_1 = ["file1.txt", "file2.txt", "file3.txt"];
export const FILE_VARIANTS_2 = [
  "reboot_skynet.exe",
  "target_list.txt",
  "terminator_blueprint.txt",
];

export const FILE_SERVICE_HANDLERS = [
  http.get(
    "/api/conversations/:conversationId/list-files",
    async ({ params }) => {
      // Make handler deterministic in tests by avoiding an unfixed delay.
      // Use a zero-duration delay which yields to the event loop but returns
      // immediately, keeping responses synchronous for Playwright runs.
      await delay(0);

      const cid = params.conversationId?.toString();
      if (!cid) {
        return HttpResponse.json(null, { status: 400 });
      }

      return cid === "test-conversation-id-2"
        ? HttpResponse.json(FILE_VARIANTS_2)
        : HttpResponse.json(FILE_VARIANTS_1);
    },
  ),

  http.get(
    "/api/conversations/:conversationId/select-file",
    async ({ request }) => {
      // Keep this handler responsive in tests; zero-duration delay avoids
      // introducing variable latency that can cause flaky timeouts.
      await delay(0);

      const url = new URL(request.url);
      const file = url.searchParams.get("file")?.toString();
      if (file) {
        return HttpResponse.json({ code: `Content of ${file}` });
      }

      return HttpResponse.json(null, { status: 404 });
    },
  ),
];
