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
  // Inject an init script to record attribute mutations on document.body and document.documentElement
  await context.addInitScript(() => {
    window.__attributeMutations = [];
    const record = (type, target, name, value) => {
      try {
        window.__attributeMutations.push({ time: Date.now(), type, target: target === document.body ? 'body' : 'documentElement', name, value });
      } catch (e) {
        // ignore
      }
    };
    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === 'attributes') {
          record('attributeChanged', m.target, m.attributeName, m.target.getAttribute(m.attributeName));
        }
      }
    });
    try {
      obs.observe(document, { attributes: true, subtree: true, attributeOldValue: true });
      // Also ensure we capture initial attributes present at start
      if (document.body) {
        for (const name of document.body.getAttributeNames()) record('initial', document.body, name, document.body.getAttribute(name));
      }
      for (const name of document.documentElement.getAttributeNames()) record('initial', document.documentElement, name, document.documentElement.getAttribute(name));
    } catch (e) {
      // ignore
    }
  });

  const routes = [
    { name: 'landing', path: '/' },
    { name: 'conversations-list', path: '/conversations' },
    { name: 'chat-1', path: '/conversations/1' },
    { name: 'settings', path: '/settings' },
    { name: 'about', path: '/about' },
  ];


  const results = [];

  for (const r of routes) {
    const page = await context.newPage();
    const url = new URL(r.path, base).href;
    try {
      console.log('Visiting', url);
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      // Wait for a stable page title selector to avoid loader/fallback snapshots
      try {
        await page.waitForSelector('[data-testid="page-title"]', { timeout: 7000 });
      } catch (e) {
        // fallback: slightly longer
        try { await page.waitForSelector('[data-testid="page-title"]', { timeout: 12000 }); } catch {}
      }
      // Give client a moment to render any remaining dynamic parts
      await page.waitForTimeout(300);

      // Capture presence of classes and a more detailed DOM snapshot for debugging
      const domInfo = await page.evaluate(() => {
        // helper to serialize an element minimally
        function serialize(el) {
          if (!el) {
            return null;
          }
          return {
            tag: el.tagName,
            id: el.id || null,
            className: el.className || null,
            text: (el.textContent || '').trim().slice(0, 300),
            outerHTML: (el.outerHTML || '').slice(0, 2000),
          };
        }

        const sectionEls = Array.from(document.querySelectorAll('.section-heading'));
        const headings = Array.from(document.querySelectorAll('h1,h2,h3')).slice(0, 8);
        const titleBySelectors = [
          document.querySelector('.page-title'),
          document.querySelector('[data-testid="page-title"]'),
          document.querySelector('[role="heading"]'),
        ].filter(Boolean);

        return {
          sectionHeadingCount: sectionEls.length,
          sectionHeadingElements: sectionEls.map(serialize),
          headingCandidates: headings.map(serialize),
          titleSelectors: titleBySelectors.map(serialize),
          documentTitle: document.title || null,
          bodyTextSample: (document.body && document.body.textContent || '').trim().slice(0, 800),
          // capture attributes on body and documentElement to detect client-side injections
          bodyAttributes: document.body ? Array.from(document.body.getAttributeNames()).reduce((acc, name) => (acc[name] = document.body.getAttribute(name), acc), {}) : {},
          documentElementAttributes: document.documentElement ? Array.from(document.documentElement.getAttributeNames()).reduce((acc, name) => (acc[name] = document.documentElement.getAttribute(name), acc), {}) : {},
          attributeMutations: window.__attributeMutations || [],
        };
      });

      const hasSectionHeading = Array.isArray(domInfo.sectionHeadingElements) && domInfo.sectionHeadingElements.length > 0;
      const hasCtaPrimary = await page.$('.cta-primary') !== null;

      const screenshotPath = path.join(outDir, `${r.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });

      const domPath = path.join(outDir, `${r.name}-dom.json`);
      fs.writeFileSync(domPath, JSON.stringify(domInfo, null, 2), 'utf8');

      results.push({
        route: r.path,
        url,
        hasSectionHeading,
        hasCtaPrimary,
        screenshot: screenshotPath,
        domJson: domPath,
      });
    } catch (err) {
      console.error('Error visiting', url, err.message);
      results.push({ route: r.path, url, error: err.message });
    } finally {
      try { await page.close(); } catch {};
    }
  }

  await browser.close();

  const summaryPath = path.join(outDir, 'summary.json');
  fs.writeFileSync(summaryPath, JSON.stringify(results, null, 2), 'utf8');
  console.log('Done. Summary written to', summaryPath);
  console.log(JSON.stringify(results, null, 2));
})();
