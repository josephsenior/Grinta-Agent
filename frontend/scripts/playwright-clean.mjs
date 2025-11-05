import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const CANDIDATES = ['http://127.0.0.1:3001/', 'http://localhost:3001/', 'http://[::1]:3001/'];
let BASE = CANDIDATES[0];
const outPath = path.resolve(process.cwd(), 'tests', 'ui-screenshots', 'playwright-clean-report.json');

(async () => {
  const report = { serverHtmlHasAttribute: false, hydratedDomHasAttribute: false, attributes: [], consoleLogs: [], errors: [], warningCount: 0 };

  try {
    // launch clean headless chromium
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();

    // fetch raw server HTML (no JS executed) using Playwright's request API
    let lastFetchErr = null;
    let workingBase = null;
    for (const candidate of CANDIDATES) {
      try {
        const resp = await context.request.get(candidate, { maxRedirects: 5, timeout: 5000 });
        const text = await resp.text();
        report.serverHtmlHasAttribute = text.includes('data-demoway-document-id');
        workingBase = candidate;
        break;
      } catch (e) {
        lastFetchErr = e;
      }
    }
    if (!workingBase) {
      report.fetchError = String(lastFetchErr);
    } else {
      BASE = workingBase; // use the working base for page navigation
    }

    const page = await context.newPage();

    page.on('console', (msg) => {
      report.consoleLogs.push({ type: msg.type(), text: msg.text() });
      if (msg.type() === 'error') {
        report.errors.push(msg.text());
      }
      if (msg.type() === 'warning') {
        report.warningCount++;
      }
    });

    // go to page and wait for load
    await page.goto(BASE, { waitUntil: 'load', timeout: 30000 });

    // allow some time for client-side scripts to run
    await page.waitForTimeout(1500);

    // inspect hydrated DOM for the attribute
    const attrs = await page.$$eval('[data-demoway-document-id]', (els) =>
      els.map((el) => el.getAttribute('data-demoway-document-id'))
    );

    report.hydratedDomHasAttribute = attrs.length > 0;
    report.attributes = attrs;

    await browser.close();
  } catch (err) {
    report.exception = String(err);
  }

  try {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
    console.log('Wrote report to', outPath);
  } catch (e) {
    console.error('Failed to write report:', e);
  }

  console.log(JSON.stringify(report, null, 2));
  if (report.serverHtmlHasAttribute) {
    process.exit(2);
  }
  if (report.hydratedDomHasAttribute) {
    process.exit(3);
  }
  process.exit(0);
})();
