import { delay, http, HttpResponse } from "msw";

export const FILE_VARIANTS_1 = ["file1.txt", "file2.txt", "file3.txt"];
export const FILE_VARIANTS_2 = [
  "reboot_skynet.exe",
  "target_list.txt",
  "terminator_blueprint.txt",
];

const createListFilesHandler = (path: string) =>
  http.get(path, async ({ params }) => {
    const cid = params.conversationId?.toString();
    if (!cid) {
      return HttpResponse.json(null, { status: 400 });
    }

    return cid === "test-conversation-id-2"
      ? HttpResponse.json(FILE_VARIANTS_2)
      : HttpResponse.json(FILE_VARIANTS_1);
  });

const createSelectFileHandler = (path: string) =>
  http.get(path, async ({ request }) => {
    const url = new URL(request.url);
    const file = url.searchParams.get("file")?.toString();
    if (file) {
      return HttpResponse.json({ code: `Content of ${file}` });
    }

    return HttpResponse.json(null, { status: 404 });
  });

export const FILE_SERVICE_HANDLERS = [
  createListFilesHandler("/api/conversations/:conversationId/list-files"),
  createListFilesHandler("/api/conversations/:conversationId/files/list-files"),
  createSelectFileHandler("/api/conversations/:conversationId/select-file"),
  createSelectFileHandler(
    "/api/conversations/:conversationId/files/select-file",
  ),
];
