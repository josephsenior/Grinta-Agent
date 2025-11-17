// filepath: /home/janardhan/Documents/code/Ai/mcp-starter-typescript/src/utils/api.ts
/**
 * Legacy API utilities for shadcn/ui components
 *
 * NOTE: This file contains legacy functions that were used for scraping shadcn.com
 * The MCP server now uses direct GitHub v4 registry access in tools.ts
 *
 * This file is kept for potential future extensions but all functions are
 * deprecated in favor of the v4 registry approach.
 */
import { z } from 'zod';
// Zod Schemas for type definitions (still useful for type safety)
const ComponentPropSchema = z.object({
    name: z.string(),
    type: z.string(),
    description: z.string(),
    required: z.boolean().optional(),
    default: z.string().optional(),
    example: z.string().optional(),
});
const ComponentExampleSchema = z.object({
    title: z.string(),
    code: z.string(),
    url: z.string().optional(),
    description: z.string().optional(),
});
const ComponentInfoSchema = z.object({
    name: z.string(),
    description: z.string(),
    url: z.string().optional(),
    props: z.array(ComponentPropSchema).optional(),
    examples: z.array(ComponentExampleSchema).optional(),
    source: z.string().optional(),
    installation: z.string().optional(),
    sourceUrl: z.string().optional(),
    usage: z.string().optional(),
});
const ThemeSchema = z.object({
    name: z.string(),
    description: z.string(),
    url: z.string().optional(),
    preview: z.string().optional(),
    author: z.string().optional(),
});
const BlockSchema = z.object({
    name: z.string(),
    description: z.string(),
    url: z.string().optional(),
    preview: z.string().optional(),
    code: z.string().optional(),
    dependencies: z.array(z.string()).optional(),
});
