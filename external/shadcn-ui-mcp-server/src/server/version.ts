export async function readVersion(fallback = '1.0.3'): Promise<string> {
  try {
    const fs = await import('fs');
    const path = await import('path');
    const { fileURLToPath } = await import('url');

    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);

    const candidates = [
      path.resolve(__dirname, '..', '..', 'package.json'),
      path.resolve(__dirname, '..', 'package.json'),
      path.resolve(process.cwd(), 'package.json'),
    ];

    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) {
        const content = fs.readFileSync(candidate, 'utf8');
        const pkg = JSON.parse(content);
        return pkg.version || fallback;
      }
    }
  } catch {
    // ignore
  }
  return fallback;
}
