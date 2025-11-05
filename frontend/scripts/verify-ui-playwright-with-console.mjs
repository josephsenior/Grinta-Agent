import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

async function waitForServer(url, timeout = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const res = await fetch(url, { method: 'HEAD' });
      if (res.ok || res.status === 200 || res.status === 204) {
        return true;
      }
    } catch (e) {
      // ignore
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

(async () => {
  const base = process.env.BASE_URL || 'http://localhost:3002';
  const outDir = path.join(process.cwd(), 'tests', 'ui-screenshots');
  fs.mkdirSync(outDir, { recursive: true });
  console.log('Waiting for server at', base);
  const ok = await waitForServer(base, 20000);
  if (!ok) {
    console.error('Server did not become reachable at', base);
    process.exit(2);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });

  const routes = [
    { name: 'landing', path: '/' },
    { name: 'conversations-list', path: '/conversations' },
    { name: 'chat-1', path: '/conversations/1' },
    { name: 'settings', path: '/settings' },
    { name: 'about', path: '/about' },
  ];

  const errors = [];
  const results = [];

  for (const r of routes) {
    const page = await context.newPage();
    // capture console messages and page errors
    page.on('console', (msg) => {
      errors.push({ type: 'console', route: r.path, text: msg.text(), location: msg.location() });
    });
    page.on('pageerror', (err) => {
      errors.push({ type: 'pageerror', route: r.path, message: err.message, stack: err.stack });
    });
    try {
      const url = new URL(r.path, base).href;
      console.log('Visiting', url);
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      try { await page.waitForSelector('[data-testid="page-title"]', { timeout: 7000 }); } catch {}
      await page.waitForTimeout(300);
      const screenshotPath = path.join(outDir, `${r.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      const domInfo = await page.evaluate(() => ({ documentTitle: document.title, bodyAttrs: document.body ? Array.from(document.body.getAttributeNames()) : [] }));
      const domPath = path.join(outDir, `${r.name}-dom.json`);
      fs.writeFileSync(domPath, JSON.stringify(domInfo, null, 2), 'utf8');
      results.push({ route: r.path, url, screenshot: screenshotPath, domJson: domPath });
    } catch (err) {
      console.error('Error visiting', r.path, err && err.message ? err.message : String(err));
      results.push({ route: r.path, error: err && err.message ? err.message : String(err) });
    } finally {
      try { await page.close(); } catch (e) {}
    }
  }

  await browser.close();
  fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(results, null, 2), 'utf8');
  fs.writeFileSync(path.join(outDir, 'errors.json'), JSON.stringify(errors, null, 2), 'utf8');
  console.log('Done. Wrote summary and errors to', outDir);
  if (errors.length) {
    console.log('Captured errors:', JSON.stringify(errors, null, 2));
  }
})();
