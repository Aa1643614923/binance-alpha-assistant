import { chromium } from 'playwright';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const baseDir = path.resolve(scriptDir, '..');
const demoPath = path.join(baseDir, 'demo', 'index.html');
const submissionPath = path.join(baseDir, 'submission', 'submission_brief.html');
const assetsDir = path.join(baseDir, 'submission', 'assets');

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1600 }, deviceScaleFactor: 1.2 });

await page.goto(pathToFileURL(demoPath).href, { waitUntil: 'load' });
await page.screenshot({ path: path.join(assetsDir, 'demo-overview.png'), fullPage: true });

const shots = [
  { tab: 's', file: 'demo-stable.png' },
  { tab: 'f', file: 'demo-futures.png' },
  { tab: 'd', file: 'demo-daily.png' },
];

for (const shot of shots) {
  await page.click(`.tab[data-tab="${shot.tab}"]`);
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(assetsDir, shot.file), fullPage: true });
}

const pdfPage = await browser.newPage({ viewport: { width: 1280, height: 1800 } });
await pdfPage.goto(pathToFileURL(submissionPath).href, { waitUntil: 'load' });
await pdfPage.waitForTimeout(800);
await pdfPage.pdf({
  path: path.join(assetsDir, 'binance_alpha_assistant_submission.pdf'),
  format: 'A4',
  printBackground: true,
  margin: { top: '16mm', right: '12mm', bottom: '16mm', left: '12mm' },
});

await browser.close();
console.log('Rendered submission assets');
