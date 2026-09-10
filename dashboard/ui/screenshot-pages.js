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
  // Public / auth
  { name: '01-login', path: '/', auth: false, action: 'open-login' },
  { name: '02-register', path: '/', auth: false, action: 'open-register' },

  // Dashboard main tabs
  { name: '03-monitor', path: '/dashboard', auth: true, tab: 'monitor', sub: 'illustration' },
  { name: '04-monitor-graph', path: '/dashboard', auth: true, tab: 'monitor', sub: 'graph' },
  { name: '05-analytics', path: '/dashboard', auth: true, tab: 'analytics' },
  { name: '06-control', path: '/dashboard', auth: true, tab: 'control' },
  { name: '07-live', path: '/dashboard', auth: true, tab: 'live' },

  // Gallery sub-filters
  { name: '08-gallery-snapshot', path: '/dashboard', auth: true, tab: 'snapshot', filter: 'snapshot' },
  { name: '09-gallery-recording', path: '/dashboard', auth: true, tab: 'snapshot', filter: 'recording' },
  { name: '10-gallery-ai', path: '/dashboard', auth: true, tab: 'snapshot', filter: 'ai' },

  // Alerts sub-tabs
  { name: '11-alerts-history', path: '/dashboard', auth: true, tab: 'alerts', sub: 'alerts' },
  { name: '12-alerts-thresholds', path: '/dashboard', auth: true, tab: 'alerts', sub: 'thresholds' },

  // Export sub-tabs
  { name: '13-export-telemetry', path: '/dashboard', auth: true, tab: 'export', sub: 'telemetry' },
  { name: '14-export-nodes', path: '/dashboard', auth: true, tab: 'export', sub: 'nodes' },

  // Module management
  { name: '15-module-list', path: '/dashboard', auth: true, tab: 'module' },
  { name: '16-module-nodes', path: '/dashboard', auth: true, tab: 'module', sub: 'node-management' },
  { name: '17-node-config', path: '/dashboard', auth: true, tab: 'module', sub: 'node-config' },

  // Admin group
  { name: '18-audit', path: '/dashboard', auth: true, tab: 'audit' },
  { name: '19-dlq', path: '/dashboard', auth: true, tab: 'dlq' },
  { name: '20-webhook-settings', path: '/dashboard', auth: true, tab: 'webhook', sub: 'settings' },
  { name: '21-webhook-logs', path: '/dashboard', auth: true, tab: 'webhook', sub: 'logs' },
  { name: '22-webhook-test', path: '/dashboard', auth: true, tab: 'webhook', sub: 'test' },
  { name: '23-users', path: '/dashboard', auth: true, tab: 'users' },

  // Profile
  { name: '24-profile', path: '/dashboard', auth: true, tab: 'profile' },
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

  async function ensureDarkMode(page) {
  await page.addInitScript(() => {
    try { localStorage.setItem('theme', 'dark'); } catch { /* ignore */ }
  });
}

async function ensureLoginModal(page) {
  const modal = page.locator('input[placeholder="Enter your email or username"]').first();
  if (await modal.count() === 0) {
    const loginBtn = page.locator('button:has-text("Login"), button:has-text("Get Started")').first();
    if (await loginBtn.count() > 0) {
      await loginBtn.click({ force: true });
      await page.waitForTimeout(3000);
    }
  }
}

async function login(page) {
  await ensureDarkMode(page);
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
  let currentTab = null;

  for (const p of PAGES) {
    const url = `${DASHBOARD_URL}${p.path}`;
    console.log(`Capturing: ${p.name} → ${url}`);

    try {
      if (p.auth) {
        if (!isAuthed) {
          await login(page);
          isAuthed = true;
        }

        // Navigate to the base tab if different from current
        if (currentTab !== p.tab) {
          await navigateToTab(page, p.tab);
          currentTab = p.tab;
        }

        // Handle sub-views within a tab
        if (p.sub === 'graph') {
          // Monitor page: switch to graph view
          const graphBtn = page.locator('button:has-text("Graph Trends")').first();
          if (await graphBtn.count() > 0) {
            await graphBtn.click();
            await page.waitForTimeout(2000);
          }
        } else if (p.sub === 'illustration') {
          // Monitor page: ensure illustration view
          const illustBtn = page.locator('button:has-text("Illustration")').first();
          if (await illustBtn.count() > 0) {
            await illustBtn.click();
            await page.waitForTimeout(2000);
          }
        } else if (p.filter) {
          // Gallery filters
          const filterBtn = page.locator(`button:has-text("${p.filter.toUpperCase()}")`).first();
          if (await filterBtn.count() > 0) {
            await filterBtn.click();
            await page.waitForTimeout(1500);
          }
        } else if (p.sub === 'alerts' || p.sub === 'thresholds') {
          // Alerts sub-tabs
          const subTabBtn = page.locator(`button:has-text("${p.sub === 'alerts' ? 'Alerts' : 'Thresholds'}")`).first();
          if (await subTabBtn.count() > 0) {
            await subTabBtn.click();
            await page.waitForTimeout(1500);
          }
        } else if (p.sub === 'telemetry' || p.sub === 'nodes') {
          // Export sub-tabs
          const subTabBtn = page.locator(`button:has-text("${p.sub === 'telemetry' ? 'Telemetry' : 'Nodes'}")`).first();
          if (await subTabBtn.count() > 0) {
            await subTabBtn.click();
            await page.waitForTimeout(1500);
          }
        } else if (p.sub === 'settings' || p.sub === 'logs' || p.sub === 'test') {
          // Webhook sub-tabs
          const labels = { settings: 'Settings', logs: 'Delivery Logs', test: 'Test' };
          const subTabBtn = page.locator(`button:has-text("${labels[p.sub]}")`).first();
          if (await subTabBtn.count() > 0) {
            await subTabBtn.click();
            await page.waitForTimeout(1500);
          }
        } else if (p.sub === 'node-management') {
          // Module -> Node Management: click "Manage / Pair Nodes" on first module
          const manageBtn = page.locator('button[title="Manage / Pair Nodes"]').first();
          if (await manageBtn.count() > 0) {
            await manageBtn.click();
            await page.waitForTimeout(3000);
          }
        } else if (p.sub === 'node-config') {
          // Module -> Node Management -> Configure on first paired node
          const configureBtn = page.locator('button:has-text("Configure")').first();
          if (await configureBtn.count() > 0) {
            await configureBtn.click();
            await page.waitForTimeout(3000);
          }
        }
      } else {
        await ensureDarkMode(page);
        await page.goto(url);
        await page.waitForTimeout(4000);

        if (p.action === 'open-login') {
          await ensureLoginModal(page);
        } else if (p.action === 'open-register') {
          const loginBtn = page.locator('button:has-text("Login"), button:has-text("Get Started")').first();
          if (await loginBtn.count() > 0) {
            await loginBtn.click({ force: true });
            await page.waitForTimeout(1000);
          }
          const createAccountBtn = page.locator('button:has-text("Create account")').first();
          if (await createAccountBtn.count() > 0) {
            await createAccountBtn.click({ force: true });
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
      } catch { /* ignore */ }
    }
  }

  await browser.close();
  console.log('\nAll screenshots captured successfully.');
}

captureScreenshots().catch((err) => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});
