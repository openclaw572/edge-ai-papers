#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { chromium } = require('/home/aaron/.hermes/hermes-agent/node_modules/playwright');

function argValue(name, fallback = null) {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && idx + 1 < process.argv.length) return process.argv[idx + 1];
  return fallback;
}
function hasFlag(name) { return process.argv.includes(name); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function clickAnyText(page, texts, timeout = 5000) {
  for (const text of texts) {
    if (!text) continue;
    const candidates = [
      page.getByRole('button', { name: new RegExp(`^${String(text).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`, 'i') }).first(),
      page.locator(`button[aria-label="${text}"]`).first(),
    ];
    for (const c of candidates) {
      try {
        await c.waitFor({ timeout: 1500 });
        await c.click({ timeout });
        return text;
      } catch {}
    }
  }
  return false;
}

async function ensureNotebookReady(page, url, sourceLabel) {
  for (let attempt = 0; attempt < 3; attempt++) {
    if (page.url() !== url) {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await sleep(2000);
    }
    const bodyText = await page.locator('body').innerText().catch(() => '');
    const hasSource = bodyText.includes(sourceLabel);
    const wrongEmptyNotebook = /Untitled notebook/i.test(bodyText) && /0\s*(sources?|個來源)/i.test(bodyText);
    const hasStudioAction = /Reports|報告|Video Overview|影片摘要/i.test(bodyText);
    if (hasSource && !wrongEmptyNotebook && hasStudioAction) return { ok: true, attempt, bodyText };
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await sleep(3000);
  }
  const finalBody = await page.locator('body').innerText().catch(() => '');
  throw new Error(`Notebook guard failed for ${url} source=${sourceLabel}\n${finalBody.slice(0, 2000)}`);
}

(async () => {
  const profile = argValue('--profile', '/home/aaron/.hermes/browser-profiles/notebooklm-b');
  const url = argValue('--url');
  const sourceLabel = argValue('--source-label');
  const reportLabel = argValue('--report-label', 'Briefing Doc');
  const artifactsDir = argValue('--artifacts', '/home/aaron/.hermes/notebooklm-artifacts');
  const headless = hasFlag('--headless');
  if (!url) throw new Error('--url is required');
  if (!sourceLabel) throw new Error('--source-label is required');

  fs.mkdirSync(artifactsDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const screenshotPath = path.join(artifactsDir, `notebooklm-generate-report-min-${stamp}.png`);
  const statePath = path.join(artifactsDir, `notebooklm-generate-report-min-${stamp}.json`);

  const context = await chromium.launchPersistentContext(profile, {
    headless,
    viewport: { width: 1440, height: 1024 },
    args: ['--disable-blink-features=AutomationControlled', '--no-default-browser-check', '--disable-dev-shm-usage'],
  });

  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await sleep(2500);
  await ensureNotebookReady(page, url, sourceLabel);

  const sourceBox = page.locator(`input[type="checkbox"][aria-label="${sourceLabel}"]`).first();
  if (await sourceBox.count()) {
    try {
      if (!(await sourceBox.isChecked())) await sourceBox.check({ timeout: 3000 });
    } catch {
      await sourceBox.click({ timeout: 3000 });
    }
  }

  const openedReports = await clickAnyText(page, ['報告', 'Reports'], 5000);
  if (!openedReports) {
    const bodyText = await page.locator('body').innerText().catch(() => '');
    throw new Error(`Could not open Reports panel\n${bodyText.slice(0, 2000)}`);
  }
  await sleep(2500);

  const labelAliases = {
    'Briefing Doc': ['Briefing Doc', 'Briefing doc', '簡介文件'],
    'Study Guide': ['Study Guide', 'Study guide', '研讀指南'],
    'Blog Post': ['Blog Post', 'Blog post', '網誌文章'],
    'Create Your Own': ['Create Your Own', 'Custom', '自訂報告'],
    'Custom': ['Custom', 'Create Your Own', '自訂報告'],
  };
  const labels = labelAliases[reportLabel] || [reportLabel, reportLabel.toLowerCase(), reportLabel.replace('Doc', 'doc')];
  let clicked = false;
  let matchedLabel = null;
  for (const label of labels) {
    const normalized = String(label).trim().toLowerCase();
    clicked = await page.evaluate((wanted) => {
      const buttons = [...document.querySelectorAll('mat-dialog-container .option-card button.primary-action-button')];
      const btn = buttons.find(el => ((el.getAttribute('aria-label') || '').trim().toLowerCase() === wanted));
      if (!btn) return false;
      btn.click();
      return true;
    }, normalized).catch(() => false);
    if (clicked) {
      matchedLabel = label;
      break;
    }
  }
  if (!clicked) throw new Error(`Could not click report format: ${reportLabel}`);

  const started = Date.now();
  let finalState = null;
  while (Date.now() - started < 20000) {
    finalState = await page.evaluate(() => {
      const bodyText = (document.body.innerText || '').trim();
      return {
        hasDialog: !!document.querySelector('mat-dialog-container'),
        generationStarted: /Generating Report|Starting Report generation|正在產生報告|based on 1 source/i.test(bodyText),
        bodyPreview: bodyText.slice(0, 4000),
      };
    });
    if (finalState.generationStarted || !finalState.hasDialog) break;
    await sleep(500);
  }

  await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
  const result = {
    ok: clicked && !!finalState,
    matchedLabel,
    screenshot: screenshotPath,
    statePath,
    state: {
      url: page.url(),
      title: await page.title(),
      sourceLabel,
      reportLabel,
      clicked,
      matchedLabel,
      finalState,
    },
  };
  fs.writeFileSync(statePath, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  await context.close();
})().catch(err => {
  console.error(JSON.stringify({ ok: false, error: String(err), stack: err?.stack || null }, null, 2));
  process.exit(1);
});
