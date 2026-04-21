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
function escapeRegex(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

function notebookIdFromUrl(url) {
  if (!url) return '';
  const m = String(url).match(/\/notebook\/([^/?#]+)/i);
  return m ? m[1] : '';
}

async function findNotebookCard(page, notebookId, titleHint) {
  const titlePattern = titleHint ? new RegExp(escapeRegex(titleHint), 'i') : null;
  for (let attempt = 0; attempt < 4; attempt++) {
    const found = await page.evaluate(({ notebookId, titleHint }) => {
      const cards = [...document.querySelectorAll('mat-card.project-button-card, .project-button-card, mat-card')];
      for (const card of cards) {
        const link = card.querySelector('a[href*="/notebook/"]');
        const href = link?.href || '';
        const text = (card.innerText || card.textContent || '').trim();
        const idMatch = notebookId && href.includes(`/notebook/${notebookId}`);
        const titleMatch = titleHint && text.includes(titleHint);
        if (!idMatch && !titleMatch) continue;
        const menuButton = card.querySelector('button.project-button-more, button[aria-label="專案動作選單"], button[aria-label="Project action menu"], button[aria-label*="action menu"], button[aria-label*="動作選單"]');
        return {
          ok: true,
          href,
          text,
          hasMenuButton: !!menuButton,
        };
      }
      return { ok: false };
    }, { notebookId, titleHint });
    if (found.ok) return found;
    await page.mouse.wheel(0, 1200).catch(() => {});
    await sleep(700);
  }

  const cardsDump = await page.evaluate(() => [...document.querySelectorAll('mat-card.project-button-card, .project-button-card, mat-card')].slice(0, 30).map(card => ({
    href: card.querySelector('a[href*="/notebook/"]')?.href || '',
    text: (card.innerText || card.textContent || '').trim().slice(0, 200),
  })));
  return { ok: false, cardsDump, notebookId, titleHint, titlePattern: titlePattern?.source || null };
}

async function clickNotebookMenu(page, notebookId, titleHint) {
  const result = await page.evaluate(({ notebookId, titleHint }) => {
    const cards = [...document.querySelectorAll('mat-card.project-button-card, .project-button-card, mat-card')];
    for (const card of cards) {
      const link = card.querySelector('a[href*="/notebook/"]');
      const href = link?.href || '';
      const text = (card.innerText || card.textContent || '').trim();
      const idMatch = notebookId && href.includes(`/notebook/${notebookId}`);
      const titleMatch = titleHint && text.includes(titleHint);
      if (!idMatch && !titleMatch) continue;
      const menuButton = card.querySelector('button.project-button-more, button[aria-label="專案動作選單"], button[aria-label="Project action menu"], button[aria-label*="action menu"], button[aria-label*="動作選單"]');
      if (!menuButton) return { ok: false, reason: 'menu-button-not-found', href, text };
      menuButton.click();
      return { ok: true, href, text };
    }
    return { ok: false, reason: 'card-not-found' };
  }, { notebookId, titleHint });
  if (!result.ok) throw new Error(`Could not open notebook action menu: ${JSON.stringify(result)}`);
  await sleep(700);
  return result;
}

async function clickDeleteMenuItem(page) {
  const candidates = [
    page.locator('button.delete-button').first(),
    page.getByRole('menuitem', { name: /^(delete|刪除)$/i }).first(),
    page.locator('[role="menuitem"]').filter({ hasText: /Delete|刪除/i }).first(),
  ];
  for (const c of candidates) {
    try {
      await c.waitFor({ timeout: 3000 });
      await c.click({ timeout: 3000 });
      await sleep(600);
      return true;
    } catch {}
  }
  const body = await page.locator('body').innerText().catch(() => '');
  throw new Error(`Delete menu item not found. Body preview:\n${body.slice(0, 2000)}`);
}

async function confirmDelete(page) {
  const dialog = page.locator('mat-dialog-container, [role="dialog"]:has-text("Delete"), [role="dialog"]:has-text("刪除")').first();
  await dialog.waitFor({ timeout: 5000 });
  const candidates = [
    dialog.getByRole('button', { name: /^Delete$/i }).first(),
    dialog.getByRole('button', { name: /^刪除$/i }).first(),
    dialog.locator('button').filter({ hasText: /^Delete$/i }).first(),
    dialog.locator('button').filter({ hasText: /^刪除$/i }).first(),
    dialog.locator('button:not(.tertiary-button)').last(),
  ];
  for (const c of candidates) {
    try {
      await c.waitFor({ timeout: 2000 });
      await c.click({ timeout: 3000 });
      await sleep(1000);
      return true;
    } catch {}
  }
  const text = await dialog.innerText().catch(() => '');
  throw new Error(`Delete confirmation button not found. Dialog:\n${text}`);
}

async function notebookStillPresent(page, notebookId, titleHint) {
  return await page.evaluate(({ notebookId, titleHint }) => {
    return [...document.querySelectorAll('a[href*="/notebook/"]')].some(a => {
      const href = a.href || '';
      const card = a.closest('mat-card.project-button-card, .project-button-card, mat-card');
      const text = (card?.innerText || card?.textContent || '').trim();
      return (notebookId && href.includes(`/notebook/${notebookId}`)) || (titleHint && text.includes(titleHint));
    });
  }, { notebookId, titleHint });
}

(async () => {
  const userDataDir = argValue('--profile', '/home/aaron/.hermes/browser-profiles/notebooklm');
  const artifactsDir = argValue('--artifacts', '/home/aaron/.hermes/notebooklm-artifacts');
  const notebookUrl = argValue('--url', '');
  const titleHint = argValue('--title-hint', '');
  const headless = hasFlag('--headless');
  const dryRun = hasFlag('--dry-run');
  const notebookId = notebookIdFromUrl(notebookUrl);
  if (!notebookId && !titleHint) throw new Error('Pass --url or --title-hint');

  fs.mkdirSync(userDataDir, { recursive: true });
  fs.mkdirSync(artifactsDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const statePath = path.join(artifactsDir, `notebooklm-delete-${stamp}.json`);
  const screenshotPath = path.join(artifactsDir, `notebooklm-delete-${stamp}.png`);

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless,
    viewport: { width: 1440, height: 1024 },
    args: ['--disable-blink-features=AutomationControlled', '--no-default-browser-check', '--disable-dev-shm-usage'],
  });
  const page = await context.newPage();
  await page.goto('https://notebooklm.google.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await sleep(2500);

  const bodyText = await page.locator('body').innerText().catch(() => '');
  if (/sign in|use your google account/i.test(bodyText) || /accounts\.google\.com/i.test(page.url())) {
    throw new Error('Profile is not logged in to NotebookLM');
  }

  const found = await findNotebookCard(page, notebookId, titleHint);
  if (!found.ok) {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    fs.writeFileSync(statePath, JSON.stringify({ ok: false, phase: 'find-card', notebookId, titleHint, found }, null, 2));
    throw new Error(`Notebook card not found on home page: ${JSON.stringify(found)}`);
  }

  if (dryRun) {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    fs.writeFileSync(statePath, JSON.stringify({ ok: true, dryRun: true, notebookId, titleHint, found, screenshotPath }, null, 2));
    console.log(JSON.stringify({ ok: true, dryRun: true, notebookId, titleHint, found, statePath, screenshotPath }, null, 2));
    await context.close();
    return;
  }

  const opened = await clickNotebookMenu(page, notebookId, titleHint);
  await clickDeleteMenuItem(page);
  const dialogText = await page.locator('mat-dialog-container, [role="dialog"]').first().innerText().catch(() => '');
  await confirmDelete(page);
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
  await sleep(2500);
  await page.goto('https://notebooklm.google.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await sleep(2000);
  const stillPresent = await notebookStillPresent(page, notebookId, titleHint);
  await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
  const result = {
    ok: !stillPresent,
    notebookId,
    titleHint,
    notebookUrl,
    opened,
    dialogText,
    stillPresent,
    statePath,
    screenshotPath,
  };
  fs.writeFileSync(statePath, JSON.stringify(result, null, 2));
  if (stillPresent) {
    throw new Error(`Notebook still present after delete confirmation: ${JSON.stringify(result)}`);
  }
  console.log(JSON.stringify(result, null, 2));
  await context.close();
})().catch(async err => {
  console.error(JSON.stringify({ ok: false, error: String(err), stack: err?.stack || null }, null, 2));
  process.exit(1);
});
