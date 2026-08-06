import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:5173';
const OUTPUT_DIR = path.resolve(__dirname, process.env.OUTPUT_DIR || '.');
const AUTH_EMAIL = process.env.AUTH_EMAIL || 'admin@smartfarm.local';
const AUTH_PASSWORD = process.env.AUTH_PASSWORD || 'admin1234';

const PAGES = [
  { name: '01-login', path: '/', auth: false, action: 'open-login' },
  { name: '02-register', path: '/', auth: false, action: 'open-register' },
  { name: '03-monitor', path: '/dashboard', auth: true, tab: 'monitor' },
  { name: '04-analytics', path: '/dashboard', auth: true, tab: 'analytics' },
  { name: '05-control', path: '/dashboard', auth: true, tab: 'control' },
  { name: '06-live', path: '/dashboard', auth: true, tab: 'live' },
  { name: '07-gallery', path: '/dashboard', auth: true, tab: 'snapshot' },
  { name: '08-alerts', path: '/dashboard', auth: true, tab: 'alerts' },
  { name: '09-export', path: '/dashboard', auth: true, tab: 'export' },
  { name: '10-module', path: '/dashboard', auth: true, tab: 'module' },
  { name: '11-audit', path: '/dashboard', auth: true, tab: 'audit' },
  { name: '12-dlq', path: '/dashboard', auth: true, tab: 'dlq' },
  { name: '13-webhook', path: '/dashboard', auth: true, tab: 'webhook' },
  { name: '14-users', path: '/dashboard', auth: true, tab: 'users' },
  { name: '15-profile', path: '/dashboard', auth: true, tab: 'profile' },
];

const TAB_LABELS = {
  monitor: 'MONITOR',
  analytics: 'ANALYTICS',
  control: 'CONTROL',
  live: 'LIVE',
  snapshot: 'GALLERY',
  alerts: 'ALERTS',
  export: 'EXPORT',
  module: 'MODULE',
  audit: 'AUDIT',
  dlq: 'DLQ',
  webhook: 'WEBHOOK',
  users: 'ACCOUNT',
  profile: 'PROFILE',
};

const ADMIN_TABS = new Set(['audit', 'dlq', 'webhook', 'users']);

async function ensureLoginModal(page) {
  const modal = page.locator('input[placeholder="Enter your email or username"]').first();
  if (await modal.count() === 0) {
    const loginBtn = page.locator('button:has-text("Login"), button:has-text("Get Started")').first();
    if (await loginBtn.count() > 0) {
      await loginBtn.click();
      await page.waitForTimeout(2000);
    }
  }
}

async function login(page) {
  await page.goto(`${DASHBOARD_URL}/`);
  await page.waitForTimeout(4000);
  
  await ensureLoginModal(page);
  
  const emailInput = page.locator('input[placeholder="Enter your email or username"]').first();
  const passwordInput = page.locator('input[placeholder="••••••••"]').first();
  const submitBtn = page.locator('button[type="submit"]').first();

  await emailInput.fill(AUTH_EMAIL);
  await passwordInput.fill(AUTH_PASSWORD);
  await submitBtn.click();

  await page.waitForURL('**/dashboard', { timeout: 20000 });
  await page.waitForTimeout(3000);
}

async function expandAdminGroup(page) {
  const adminLabel = 'ADMINISTRATOR';
  const adminBtn = page.locator(`button:has-text("${adminLabel}")`).first();
  if (await adminBtn.count() === 0) return false;

  const isExpanded = await adminBtn.evaluate(el => {
    const svg = el.querySelector('svg[class*="rotate-180"], svg[style*="rotate"]');
    return svg !== null;
  }).catch(() => false);

  if (!isExpanded) {
    await adminBtn.click();
    await page.waitForTimeout(1000);
  }
  return true;
}

async function navigateToTab(page, tab) {
  const label = TAB_LABELS[tab];
  if (!label) return;

  if (ADMIN_TABS.has(tab)) {
    await expandAdminGroup(page);
  }

  const sidebarBtn = page.locator(`button:has-text("${label}")`).first();
  if (await sidebarBtn.count() > 0) {
    await sidebarBtn.click();
  } else {
    await page.goto(`${DASHBOARD_URL}/dashboard?tab=${tab}`);
  }
  await page.waitForTimeout(2500);
}

async function captureScreenshots() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  let isAuthed = false;

  for (const p of PAGES) {
    const url = `${DASHBOARD_URL}${p.path}`;
    console.log(`Capturing: ${p.name} → ${url}`);

    try {
      if (p.auth) {
        if (!isAuthed) {
          await login(page);
          isAuthed = true;
        }
        await navigateToTab(page, p.tab);
      } else {
        await page.goto(url);
        await page.waitForTimeout(4000);
        
        if (p.action === 'open-login') {
          await ensureLoginModal(page);
        } else if (p.action === 'open-register') {
          const loginBtn = page.locator('button:has-text("Login"), button:has-text("Get Started")').first();
          if (await loginBtn.count() > 0) {
            await loginBtn.click();
            await page.waitForTimeout(1000);
          }
          const createAccountBtn = page.locator('button:has-text("Create account")').first();
          if (await createAccountBtn.count() > 0) {
            await createAccountBtn.click();
            await page.waitForTimeout(2000);
          }
        }
      }

      const currentUrl = page.url();
      console.log(`  URL: ${currentUrl}`);

      const filePath = path.join(OUTPUT_DIR, `${p.name}.png`);
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`  Saved: ${filePath}`);
    } catch (err) {
      console.error(`  Failed: ${p.name} — ${err.message}`);
      try {
        const failPath = path.join(OUTPUT_DIR, `${p.name}-error.png`);
        await page.screenshot({ path: failPath, fullPage: false });
        console.log(`  Error screenshot: ${failPath}`);
      } catch {}
    }
  }

  await browser.close();
  console.log('\nAll screenshots captured successfully.');
}

captureScreenshots().catch((err) => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});
