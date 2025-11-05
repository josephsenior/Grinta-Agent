import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { capabilities } from './capabilities.js';

export function createServer(version: string) {
  return new Server(
    {
      name: 'shadcn-ui-mcp-server',
      version,
    },
    {
      capabilities,
    }
  );
}
