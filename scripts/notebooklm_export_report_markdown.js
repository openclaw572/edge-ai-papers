#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { chromium } = require('/home/aaron/.hermes/hermes-agent/node_modules/playwright');

function argValue(name, fallback = null) {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && idx + 1 < process.argv.length) return process.argv[idx + 1];
  return fallback;
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

(async () => {
  const url = argValue('--url');
  const profile = argValue('--profile', '/home/aaron/.hermes/browser-profiles/notebooklm');
  const extensionPath = argValue('--extension-path', '/home/aaron/.config/google-chrome/Profile 1/Extensions/afchokljnhhggkhedfbmkcmdagjmjchj/1.0.9_0');
  const titleHint = argValue('--title-hint', '');
  const exportIndex = Number(argValue('--export-index', '-1'));
  const downloadsDir = argValue('--downloads-dir', '/tmp/notebooklm-export-downloads');
  const output = argValue('--output');
  const artifactsDir = argValue('--artifacts-dir', '/tmp/notebooklm-export-artifacts');
  if (!url) throw new Error('--url is required');

  fs.mkdirSync(downloadsDir, { recursive: true });
  fs.mkdirSync(artifactsDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const screenshotPath = path.join(artifactsDir, `export-report-${stamp}.png`);
  const statePath = path.join(artifactsDir, `export-report-${stamp}.json`);

  const context = await chromium.launchPersistentContext(profile, {
    headless: false,
    acceptDownloads: true,
    downloadsPath: downloadsDir,
    viewport: { width: 1600, height: 1100 },
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`,
      '--disable-dev-shm-usage',
      '--no-default-browser-check',
    ],
  });

  const page = context.pages()[0] || await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await sleep(3000);

  const chosen = await page.evaluate(({ titleHint, exportIndex }) => {
    const buttons = [...document.querySelectorAll('button[aria-label="Export报告"]')];
    let target = null;
    let matchedIndex = -1;

    if (exportIndex >= 0 && buttons[exportIndex]) {
      target = buttons[exportIndex];
      matchedIndex = exportIndex;
    } else if (titleHint) {
      for (let i = 0; i < buttons.length; i++) {
        const btn = buttons[i];
        const card = btn.closest('artifact-library-item') || btn.closest('article') || btn.parentElement?.parentElement || btn.parentElement;
        const cardText = (card?.innerText || '').trim();
        if (cardText && cardText.toLowerCase().includes(titleHint.toLowerCase())) {
          target = btn;
          matchedIndex = i;
          const matchedText = cardText;
          target.click();
          return { clicked: true, matchedIndex, matchedText, count: buttons.length, strategy: 'title-hint' };
        }
      }
    }

    if (!target && buttons.length) {
      target = buttons[buttons.length - 1];
      matchedIndex = buttons.length - 1;
    }
    if (!target) return { clicked: false, count: buttons.length };
    const matchedText = (target.parentElement?.parentElement?.innerText || target.parentElement?.innerText || '').trim();
    target.click();
    return { clicked: true, matchedIndex, matchedText, count: buttons.length, strategy: exportIndex >= 0 ? 'index' : 'fallback-last' };
  }, { titleHint, exportIndex });

  if (!chosen.clicked) throw new Error(`No Export报告 button found: ${JSON.stringify(chosen)}`);
  await sleep(1500);

  const modalState = await page.evaluate(() => {
    const host = document.querySelector('plasmo-csui');
    if (!host?.shadowRoot) return { hasHost: !!host, hasShadow: false };
    const buttons = [...host.shadowRoot.querySelectorAll('button')].map((b, i) => ({ i, text: (b.innerText || b.textContent || '').trim() }));
    return {
      hasHost: true,
      hasShadow: true,
      buttons,
      text: (host.shadowRoot.textContent || '').trim().slice(0, 4000),
    };
  });

  const downloadPromise = page.waitForEvent('download', { timeout: 20000 }).catch(() => null);
  const clickedExportFile = await page.evaluate(() => {
    const host = document.querySelector('plasmo-csui');
    if (!host?.shadowRoot) return { clicked: false, reason: 'no-shadow-root' };
    const buttons = [...host.shadowRoot.querySelectorAll('button')];
    const markdownBtn = buttons.find(b => (b.innerText || b.textContent || '').toLowerCase().includes('markdown'));
    if (markdownBtn) markdownBtn.click();
    const exportFileBtn = buttons.find(b => (b.innerText || b.textContent || '').trim() === 'Export File');
    if (!exportFileBtn) return { clicked: false, reason: 'no-export-file-button', buttons: buttons.map(b => (b.innerText || b.textContent || '').trim()).filter(Boolean) };
    exportFileBtn.click();
    return { clicked: true };
  });

  const download = await downloadPromise;
  let suggestedFilename = null;
  let savedAs = null;
  if (download) {
    suggestedFilename = download.suggestedFilename();
    savedAs = output || path.join(downloadsDir, suggestedFilename);
    await download.saveAs(savedAs);
  }

  await sleep(1000);
  await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
  const files = fs.readdirSync(downloadsDir).map(name => ({ name, size: fs.statSync(path.join(downloadsDir, name)).size }));
  const state = {
    pageTitle: await page.title(),
    pageUrl: page.url(),
    chosen,
    modalState,
    clickedExportFile,
    download: !!download,
    suggestedFilename,
    savedAs,
    files,
  };
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
  console.log(JSON.stringify({ ok: true, screenshotPath, statePath, state }, null, 2));
  await context.close();
})().catch(err => {
  console.error(JSON.stringify({ ok: false, error: String(err), stack: err?.stack || null }, null, 2));
  process.exit(1);
});
