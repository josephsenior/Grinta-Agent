"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const config_1 = require("vitest/config");
const path_1 = __importDefault(require("path"));
// Use the current working directory for resolving project paths. Avoids
// relying on `import.meta.url` which can trigger errors when the TS project
// is configured to emit CommonJS.
const projectRoot = process.cwd();
exports.default = (0, config_1.defineConfig)({
    root: 'frontend',
    resolve: {
        alias: {
            '#': path_1.default.resolve(projectRoot, 'frontend/src'),
            '#/': `${path_1.default.resolve(projectRoot, 'frontend/src')}/`,
        },
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './vitest.setup.ts',
    },
});
