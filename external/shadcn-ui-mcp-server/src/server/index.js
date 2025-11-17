import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { setupHandlers } from './handler.js';
import { validateFrameworkSelection, getAxiosImplementation } from '../utils/framework.js';
import { logError, logInfo, logWarning } from '../utils/logger.js';
import { parseArgs } from '../cli/args.js';
import { readVersion } from '../server/version.js';
import { createServer } from '../server/createServer.js';
export async function start() {
    try {
        logInfo('Starting Shadcn UI MCP Server...');
        const { githubApiKey } = parseArgs();
        validateFrameworkSelection();
        const axios = await getAxiosImplementation();
        if (githubApiKey) {
            axios.setGitHubApiKey(githubApiKey);
            logInfo('GitHub API configured with token');
        }
        else {
            logWarning('No GitHub API key provided. Rate limited to 60 requests/hour.');
        }
        const version = await readVersion('1.0.3');
        const server = createServer(version);
        setupHandlers(server);
        const transport = new StdioServerTransport();
        logInfo('Transport initialized: stdio');
        await server.connect(transport);
        logInfo('Server started successfully');
    }
    catch (error) {
        logError('Failed to start server', error);
        process.exit(1);
    }
}
