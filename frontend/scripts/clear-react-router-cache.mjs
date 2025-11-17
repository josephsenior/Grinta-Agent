#!/usr/bin/env node
/**
 * Clear React Router v7 build cache to force route manifest regeneration
 * This fixes issues where new routes aren't recognized
 */

import { rmSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, "..");

const cacheDirs = [
  join(rootDir, ".react-router"),
  join(rootDir, "node_modules", ".vite"),
  join(rootDir, "build", ".react-router"),
];

console.log("Clearing React Router cache...");

let cleared = false;
for (const dir of cacheDirs) {
  if (existsSync(dir)) {
    try {
      rmSync(dir, { recursive: true, force: true });
      console.log(`✓ Cleared: ${dir}`);
      cleared = true;
    } catch (error) {
      console.warn(`⚠ Could not clear ${dir}:`, error.message);
    }
  }
}

if (!cleared) {
  console.log("No cache directories found to clear.");
} else {
  console.log("\n✓ Cache cleared! Restart your dev server to regenerate routes.");
}

