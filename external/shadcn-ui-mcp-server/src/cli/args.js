export function parseArgs(argv = process.argv.slice(2)) {
    const githubApiKeyIndex = argv.findIndex((arg) => arg === '--github-api-key' || arg === '-g');
    let githubApiKey = null;
    if (githubApiKeyIndex !== -1 && argv[githubApiKeyIndex + 1]) {
        githubApiKey = argv[githubApiKeyIndex + 1];
    }
    else if (process.env.GITHUB_PERSONAL_ACCESS_TOKEN) {
        githubApiKey = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
    }
    return { githubApiKey };
}
