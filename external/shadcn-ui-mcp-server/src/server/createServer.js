import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { capabilities } from './capabilities.js';
export function createServer(version) {
    return new Server({
        name: 'shadcn-ui-mcp-server',
        version,
    }, {
        capabilities,
    });
}
