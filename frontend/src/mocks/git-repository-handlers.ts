import { delay, http, HttpResponse } from "msw";
import { GitRepository, Branch, PaginatedBranchesResponse } from "#/types/git";
import { Provider } from "#/types/settings";
import { RepositoryMicroagent } from "#/types/microagent-management";
import { MicroagentContentResponse } from "#/api/forge.types";

// Generate a list of mock repositories with realistic data
const generateMockRepositories = (
  count: number,
  provider: Provider,
): GitRepository[] =>
  Array.from({ length: count }, (_, i) => ({
    id: `${i + 1}`,
    full_name: `user/repo-${i + 1}`,
    git_provider: provider,
    is_public: Math.random() > 0.3, // 70% chance of being public
    stargazers_count: Math.floor(Math.random() * 1000),
    pushed_at: new Date(
      Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000,
    ).toISOString(), // Last 90 days
    owner_type: Math.random() > 0.7 ? "organization" : "user", // 30% chance of being organization
  }));

// Generate mock branches for a repository
const generateMockBranches = (count: number): Branch[] =>
  Array.from({ length: count }, (_, i) => ({
    name: (() => {
      if (i === 0) {
        return "main";
      }
      if (i === 1) {
        return "develop";
      }
      return `feature/branch-${i}`;
    })(),
    commit_sha: `abc123${i.toString().padStart(3, "0")}`,
    protected: i === 0, // main branch is protected
    last_push_date: new Date(
      Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000,
    ).toISOString(),
  }));

// Generate mock microagents for a repository
const generateMockMicroagents = (count: number): RepositoryMicroagent[] =>
  Array.from({ length: count }, (_, i) => ({
    name: `microagent-${i + 1}`,
    path: `.Forge/microagents/microagent-${i + 1}.md`,
    created_at: new Date(
      Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000,
    ).toISOString(),
    git_provider: "github",
  }));

// Mock repositories for each provider
const MOCK_REPOSITORIES = {
  github: generateMockRepositories(120, "github"),
  gitlab: generateMockRepositories(120, "gitlab"),
  bitbucket: generateMockRepositories(120, "bitbucket"),
};

// Mock branches (same for all repos for simplicity)
const MOCK_BRANCHES = generateMockBranches(25);

// Mock microagents (same for all repos for simplicity)
const MOCK_MICROAGENTS = generateMockMicroagents(5);

export const GIT_REPOSITORY_HANDLERS = [
  http.get("/api/user/repositories", async ({ request }) => {
    await delay(500); // Simulate network delay

    const params = new URL(request.url).searchParams;
    const queryParams = extractRepositoryQueryParams(params);

    if (!queryParams.selectedProvider) {
      return HttpResponse.json(
        "Git provider token required. (such as GitHub).",
        { status: 401 },
      );
    }

    const repositories = resolveRepositories(queryParams.selectedProvider);
    const sortedRepos = sortRepositories(repositories, queryParams.sort);
    const filteredRepos = filterRepositoriesByInstallation(
      sortedRepos,
      queryParams.selectedProvider,
      queryParams.installationId,
    );

    const pagination = paginateRepositories(
      filteredRepos,
      queryParams.page,
      queryParams.perPage,
    );

    const responseRepos = attachLinkHeader(
      pagination.items,
      buildLinkHeader(queryParams, pagination),
    );

    return HttpResponse.json(responseRepos);
  }),

  http.get("/api/user/search/repositories", async ({ request }) => {
    await delay(300); // Simulate network delay

    const url = new URL(request.url);
    const query = url.searchParams.get("query") || "";
    const selectedProvider = url.searchParams.get("selected_provider");
    const perPage = parseInt(url.searchParams.get("per_page") || "5", 10);
    const sort = url.searchParams.get("sort") || "stars";
    const order = url.searchParams.get("order") || "desc";

    // Simulate authentication error if no provider token
    if (!selectedProvider) {
      return HttpResponse.json("Git provider token required.", {
        status: 401,
      });
    }

    // Get repositories for the selected provider
    const repositories =
      MOCK_REPOSITORIES[selectedProvider as keyof typeof MOCK_REPOSITORIES] ||
      [];

    // Filter repositories by search query
    const filteredRepos = repositories.filter((repo) =>
      repo.full_name.toLowerCase().includes(query.toLowerCase()),
    );

    // Sort repositories
    const sortedRepos = [...filteredRepos];
    if (sort === "stars") {
      sortedRepos.sort((a, b) => {
        const aStars = a.stargazers_count || 0;
        const bStars = b.stargazers_count || 0;
        return order === "desc" ? bStars - aStars : aStars - bStars;
      });
    }

    // Limit results
    const limitedRepos = sortedRepos.slice(0, perPage);

    return HttpResponse.json(limitedRepos);
  }),

  // Repository branches endpoint
  http.get("/api/user/repository/branches", async ({ request }) => {
    await delay(300);

    const url = new URL(request.url);
    const repository = url.searchParams.get("repository");
    const page = parseInt(url.searchParams.get("page") || "1", 10);
    const perPage = parseInt(url.searchParams.get("per_page") || "30", 10);

    if (!repository) {
      return HttpResponse.json("Repository parameter is required", {
        status: 400,
      });
    }

    // Calculate pagination
    const startIndex = (page - 1) * perPage;
    const endIndex = startIndex + perPage;
    const paginatedBranches = MOCK_BRANCHES.slice(startIndex, endIndex);
    const hasNextPage = endIndex < MOCK_BRANCHES.length;

    const response: PaginatedBranchesResponse = {
      branches: paginatedBranches,
      has_next_page: hasNextPage,
      current_page: page,
      per_page: perPage,
      total_count: MOCK_BRANCHES.length,
    };

    return HttpResponse.json(response);
  }),

  // Search repository branches endpoint
  http.get("/api/user/search/branches", async ({ request }) => {
    await delay(200);

    const url = new URL(request.url);
    const repository = url.searchParams.get("repository");
    const query = url.searchParams.get("query") || "";
    const perPage = parseInt(url.searchParams.get("per_page") || "30", 10);

    if (!repository) {
      return HttpResponse.json("Repository parameter is required", {
        status: 400,
      });
    }

    // Filter branches by search query
    const filteredBranches = MOCK_BRANCHES.filter((branch) =>
      branch.name.toLowerCase().includes(query.toLowerCase()),
    );

    // Limit results
    const limitedBranches = filteredBranches.slice(0, perPage);

    return HttpResponse.json(limitedBranches);
  }),

  // Repository microagents endpoint
  http.get(
    "/api/user/repository/:owner/:repo/microagents",
    async ({ params }) => {
      await delay(400);

      const { owner, repo } = params;

      if (!owner || !repo) {
        return HttpResponse.json("Owner and repo parameters are required", {
          status: 400,
        });
      }

      return HttpResponse.json(MOCK_MICROAGENTS);
    },
  ),

  // Repository microagent content endpoint
  http.get(
    "/api/user/repository/:owner/:repo/microagents/content",
    async ({ request, params }) => {
      await delay(300);

      const { owner, repo } = params;
      const url = new URL(request.url);
      const filePath = url.searchParams.get("file_path");

      if (!owner || !repo || !filePath) {
        return HttpResponse.json(
          "Owner, repo, and file_path parameters are required",
          { status: 400 },
        );
      }

      // Find the microagent by path
      const microagent = MOCK_MICROAGENTS.find((m) => m.path === filePath);

      if (!microagent) {
        return HttpResponse.json("Microagent not found", { status: 404 });
      }

      const response: MicroagentContentResponse = {
        content: `# ${microagent.name}

A helpful microagent for repository tasks.

## Instructions

This microagent helps with specific tasks related to the repository.

### Usage

1. Describe your task clearly
2. The microagent will analyze the context
3. Follow the provided recommendations

### Capabilities

- Code analysis
- Task automation
- Best practice recommendations
- Error detection and resolution

---

*Generated mock content for ${microagent.name}*`,
        path: microagent.path,
        git_provider: "github",
        triggers: ["code review", "bug fix", "feature development"],
      };

      return HttpResponse.json(response);
    },
  ),
];

function extractRepositoryQueryParams(params: URLSearchParams) {
  return {
    selectedProvider: params.get("selected_provider"),
    page: parseInt(params.get("page") || "1", 10),
    perPage: parseInt(params.get("per_page") || "30", 10),
    sort: params.get("sort") || "pushed",
    installationId: params.get("installation_id"),
  } as const;
}

function resolveRepositories(provider: string | null) {
  if (!provider) {
    return [] as GitRepository[];
  }
  return (
    MOCK_REPOSITORIES[provider as keyof typeof MOCK_REPOSITORIES] || []
  );
}

function sortRepositories(repositories: GitRepository[], sort: string) {
  if (sort === "stars") {
    return [...repositories].sort(
      (a, b) => (b.stargazers_count || 0) - (a.stargazers_count || 0),
    );
  }

  if (sort === "pushed") {
    return [...repositories].sort(
      (a, b) =>
        new Date(b.pushed_at!).getTime() - new Date(a.pushed_at!).getTime(),
    );
  }

  return repositories;
}

function filterRepositoriesByInstallation(
  repositories: GitRepository[],
  provider: string | null,
  installationId: string | null,
) {
  if (!installationId || provider !== "github") {
    return repositories;
  }

  const installationIndex = parseInt(installationId, 10) || 0;
  const startRepo = installationIndex * 20;
  return repositories.slice(startRepo, startRepo + 20);
}

function paginateRepositories(
  repositories: GitRepository[],
  page: number,
  perPage: number,
) {
  const startIndex = (page - 1) * perPage;
  const endIndex = startIndex + perPage;
  const items = repositories.slice(startIndex, endIndex);

  return {
    items,
    hasNextPage: endIndex < repositories.length,
    hasPrevPage: page > 1,
    totalPages: Math.ceil(repositories.length / perPage),
    page,
    perPage,
  } as const;
}

function buildLinkHeader(
  params: ReturnType<typeof extractRepositoryQueryParams>,
  pagination: ReturnType<typeof paginateRepositories>,
) {
  if (!pagination.hasNextPage && !pagination.hasPrevPage) {
    return "";
  }

  const links = [];
  if (pagination.hasPrevPage) {
    links.push(
      `</api/user/repositories?page=${pagination.page - 1}&per_page=${pagination.perPage}>; rel="prev"`,
    );
  }
  if (pagination.hasNextPage) {
    links.push(
      `</api/user/repositories?page=${pagination.page + 1}&per_page=${pagination.perPage}>; rel="next"`,
    );
  }
  links.push(
    `</api/user/repositories?page=${pagination.totalPages}&per_page=${pagination.perPage}>; rel="last"`,
  );
  links.push(
    `</api/user/repositories?page=1&per_page=${pagination.perPage}>; rel="first"`,
  );

  return links.join(", ");
}

function attachLinkHeader(repositories: GitRepository[], linkHeader: string) {
  if (!linkHeader || repositories.length === 0) {
    return repositories;
  }

  const [first, ...rest] = repositories;
  return [{ ...first, link_header: linkHeader }, ...rest];
}
