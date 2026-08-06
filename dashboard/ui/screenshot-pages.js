import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:5173';
const OUTPUT_DIR = path.resolve(process.env.OUTPUT_DIR || './ui');
const AUTH_EMAIL = process.env.AUTH_EMAIL || 'admin@example.com';
const AUTH_PASSWORD = process.env.AUTH_PASSWORD || 'admin123';

const PAGES = [
  { name: '01-login', path: '/', auth: false },
  { name: '02-register', path: '/?mode=register', auth: false },
  { name: '03-dashboard-monitor', path: '/dashboard', auth: true, tab: 'monitor' },
  { name: '04-module-management', path: '/dashboard', auth: true, tab: 'module' },
  { name: '05-control-panel', path: '/dashboard', auth: true, tab: 'control' },
  { name: '06-analytics', path: '/dashboard', auth: true, tab: 'analytics' },
  { name: '07-live-view', path: '/dashboard', auth: true, tab: 'live' },
  { name: '08-gallery', path: '/dashboard', auth: true, tab: 'snapshot' },
  { name: '09-monitor', path: '/dashboard', auth: true, tab: 'monitor' },
  { name: '10-audit', path: '/dashboard', auth: true, tab: 'audit' },
  { name: '11-alerts', path: '/dashboard', auth: true, tab: 'alerts' },
  { name: '12-export', path: '/dashboard', auth: true, tab: 'export' },
  { name: '13-webhook', path: '/dashboard', auth: true, tab: 'webhook' },
  { name: '14-dlq', path: '/dashboard', auth: true, tab: 'dlq' },
  { name: '15-users', path: '/dashboard', auth: true, tab: 'users' },
  { name: '16-profile', path: '/dashboard', auth: true, tab: 'profile' },
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

async function login(page) {
  await page.goto(`${DASHBOARD_URL}/`);
  await page.waitForSelector('input[placeholder="Enter your email or username"]', { timeout: 10000 });
  const emailInput = page.locator('input[placeholder="Enter your email or username"]').first();
  const passwordInput = page.locator('input[placeholder="••••••••"]').first();
  const submitBtn = page.locator('button[type="submit"], button:has-text("Sign In")').first();

  await emailInput.fill(AUTH_EMAIL);
  await passwordInput.fill(AUTH_PASSWORD);
  await submitBtn.click();

  await page.waitForURL('**/dashboard', { timeout: 10000 });
  await page.waitForTimeout(2000);
}

async function navigateToTab(page, tab) {
  const label = TAB_LABELS[tab];
  if (!label) return;

  const sidebarBtn = page.locator(`button:has-text("${label}")`).first();
  if (await sidebarBtn.count() > 0) {
    await sidebarBtn.click();
  } else {
    await page.goto(`${DASHBOARD_URL}/dashboard?tab=${tab}`);
  }
  await page.waitForTimeout(1500);
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

    if (p.auth) {
      if (!isAuthed) {
        await login(page);
        isAuthed = true;
      }
      await navigateToTab(page, p.tab);
    } else {
      await page.goto(url);
      await page.waitForTimeout(1500);
    }

    const filePath = path.join(OUTPUT_DIR, `${p.name}.png`);
    await page.screenshot({ path: filePath, fullPage: false });
    console.log(`  Saved: ${filePath}`);
  }

  await browser.close();
  console.log('\nAll screenshots captured successfully.');
}

captureScreenshots().catch((err) => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});
