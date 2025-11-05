import type { Config } from "@react-router/dev/config";

/**
 * This script is used to unpack the client directory from the frontend build directory.
 * Remix SPA mode builds the client directory into the build directory. This function
 * moves the contents of the client directory to the build directory and then removes the
 * client directory.
 *
 * This script is used in the buildEnd function of the Vite config.
 */
const unpackClientDirectory = async () => {
  const fs = await import("fs");
  const path = await import("path");

  const buildDir = path.resolve(__dirname, "build");
  const clientDir = path.resolve(buildDir, "client");

  const files = await fs.promises.readdir(clientDir);
  await Promise.all(
    files.map(async (file) => {
      const src = path.resolve(clientDir, file);
      const dest = path.resolve(buildDir, file);
      try {
        // If destination already exists (Windows may lock/deny rename), remove it first
        try {
          await fs.promises.rm(dest, { recursive: true, force: true });
        } catch (e) {
          // ignore
        }
        await fs.promises.rename(src, dest);
      } catch (err) {
        // On Windows, rename can fail due to locks; fall back to copy + unlink
        try {
          const stat = await fs.promises.stat(src);
          if (stat.isDirectory()) {
            // Recursive copy
            await fs.promises.cp(src, dest, { recursive: true });
            await fs.promises.rm(src, { recursive: true, force: true });
          } else {
            await fs.promises.copyFile(src, dest);
            await fs.promises.unlink(src);
          }
        } catch (inner) {
          // If fallback fails, rethrow original error to surface build failures
          throw err;
        }
      }
    }),
  );

  await fs.promises.rmdir(clientDir);
};

export default {
  appDirectory: "src",
  // Disable SSR for pure SPA mode
  ssr: false,
} satisfies Config;
