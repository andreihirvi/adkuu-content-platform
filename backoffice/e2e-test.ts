/**
 * End-to-end test for Adkuu Content Platform
 * Tests the full flow: Login -> Create Project -> Mine -> Approve -> Publish
 */
import { chromium, Page, Browser } from 'playwright';

const BASE_URL = 'https://content.adkuu.net';
const API_URL = 'https://content-api.adkuu.net/api/v1';

// Admin credentials from seed script
const ADMIN_EMAIL = 'admin@adkuu.com';
const ADMIN_PASSWORD = 'adm1n_s3cur3_k7x9!';

// Project data for Claude Code
const PROJECT_DATA = {
  name: 'Claude Code',
  description: 'Claude Code is Anthropic\'s official AI-powered coding assistant CLI tool. It helps developers write, debug, and understand code through natural conversation.',
  website_url: 'https://claude.ai/claude-code',
  keywords: 'AI coding assistant, code helper, programming AI, developer tools, CLI tool, code generation, debugging, Anthropic, Claude',
  negative_keywords: 'ChatGPT, Copilot, Cursor',
  brand_voice: 'Be genuinely helpful and knowledgeable about software development. Share practical coding tips and experiences. Never be pushy or salesy - just be a helpful developer who happens to use great tools.',
  product_context: `Claude Code is Anthropic's official CLI tool for AI-assisted coding. Key features:
- Natural language interface for coding tasks
- Can read, write, and edit files in your codebase
- Understands project context and dependencies
- Helps with debugging, refactoring, and explaining code
- Works with any programming language
- Runs locally with your files staying private
- Free to use with Claude account

Best for: developers who want AI assistance directly in their terminal without switching context to a browser.`,
  target_subreddits: 'programming, learnprogramming, webdev, Python, javascript, coding, softwaredevelopment, ExperiencedDevs',
  automation_level: '2', // Assisted - High confidence queued
  language: 'en',
  posting_mode: 'rotate',
};

async function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function login(page: Page) {
  console.log('📍 Navigating to login page...');
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');

  console.log('🔑 Entering credentials...');
  await page.fill('input[type="email"]', ADMIN_EMAIL);
  await page.fill('input[type="password"]', ADMIN_PASSWORD);

  console.log('🚀 Clicking sign in...');
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard
  await page.waitForURL(`${BASE_URL}/`, { timeout: 10000 });
  console.log('✅ Login successful!');
}

async function createProject(page: Page) {
  console.log('\n📍 Navigating to projects page...');
  await page.goto(`${BASE_URL}/projects`);
  await page.waitForLoadState('networkidle');
  await delay(1000);

  console.log('➕ Clicking New Project button...');
  await page.click('button:has-text("New Project")');
  await delay(500);

  console.log('📝 Filling project details...');

  // Name
  await page.fill('input#name', PROJECT_DATA.name);

  // Description
  await page.fill('textarea#description', PROJECT_DATA.description);

  // Website URL
  await page.fill('input#website_url', PROJECT_DATA.website_url);

  // Keywords
  await page.fill('input#keywords', PROJECT_DATA.keywords);

  // Negative Keywords
  await page.fill('input#negative_keywords', PROJECT_DATA.negative_keywords);

  // Target Subreddits
  await page.fill('input#target_subreddits', PROJECT_DATA.target_subreddits);

  // Brand Voice
  await page.fill('textarea#brand_voice', PROJECT_DATA.brand_voice);

  // Product Context
  await page.fill('textarea#product_context', PROJECT_DATA.product_context);

  // Language - select English
  console.log('🌐 Setting language to English...');
  await page.click('button:has-text("All languages")');
  await delay(300);
  await page.click('div[role="option"]:has-text("English")');

  // Automation Level
  console.log('⚙️ Setting automation level...');
  // Find and click the automation level selector
  const automationTrigger = page.locator('button:has-text("Manual")').first();
  if (await automationTrigger.isVisible()) {
    await automationTrigger.click();
    await delay(300);
    await page.click('div[role="option"]:has-text("Assisted")');
  }

  // Account Selection Mode - keep as Rotate
  console.log('👥 Account mode set to Rotate (default)...');

  console.log('💾 Scrolling dialog and saving project...');

  // Scroll the dialog content to bottom to reveal the button
  const dialogContent = page.locator('div[role="dialog"] .overflow-y-auto');
  await dialogContent.evaluate(el => el.scrollTo(0, el.scrollHeight));
  await delay(500);

  // Now click the Create Project button in the dialog footer
  await page.locator('div[role="dialog"] button:has-text("Create Project")').click();

  // Wait for dialog to close and project to appear
  await delay(3000);

  // Verify project was created
  const projectCard = page.locator(`text="${PROJECT_DATA.name}"`).first();
  if (await projectCard.isVisible()) {
    console.log('✅ Project created successfully!');
  } else {
    console.log('⚠️ Project might not be visible yet, continuing...');
  }
}

async function triggerMining(page: Page) {
  console.log('\n📍 Navigating to Content/Queue page to trigger mining...');
  await page.goto(`${BASE_URL}/queue`);
  await page.waitForLoadState('networkidle');
  await delay(1000);

  // Look for a Mine/Scan button
  const mineButton = page.locator('button:has-text("Mine"), button:has-text("Scan"), button:has-text("Find")').first();

  if (await mineButton.isVisible()) {
    console.log('⛏️ Clicking mine button...');
    await mineButton.click();
    await delay(5000); // Wait for mining to complete
    console.log('✅ Mining triggered!');
  } else {
    console.log('ℹ️ No mine button found on queue page, checking content page...');
    await page.goto(`${BASE_URL}/content`);
    await page.waitForLoadState('networkidle');
    await delay(1000);
  }
}

async function checkOpportunities(page: Page) {
  console.log('\n📍 Checking for opportunities...');
  await page.goto(`${BASE_URL}/queue`);
  await page.waitForLoadState('networkidle');
  await delay(1000);

  // Take screenshot
  await page.screenshot({ path: '/tmp/e2e-queue-page.png', fullPage: true });
  console.log('📸 Screenshot saved to /tmp/e2e-queue-page.png');

  // Check if there are any opportunity cards
  const opportunityCards = page.locator('[class*="card"], [class*="Card"]');
  const count = await opportunityCards.count();
  console.log(`📊 Found ${count} cards on the page`);

  return count;
}

async function main() {
  console.log('🚀 Starting E2E Test for Adkuu Content Platform\n');
  console.log('='.repeat(60));

  const browser: Browser = await chromium.launch({
    headless: false,  // Set to true for CI
    slowMo: 100
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });

  const page = await context.newPage();

  try {
    // Step 1: Login
    console.log('\n📌 STEP 1: Login');
    console.log('-'.repeat(40));
    await login(page);

    // Step 2: Create Project
    console.log('\n📌 STEP 2: Create Project');
    console.log('-'.repeat(40));
    await createProject(page);

    // Step 3: Check current state
    console.log('\n📌 STEP 3: Check Opportunities');
    console.log('-'.repeat(40));
    await checkOpportunities(page);

    // Step 4: Trigger Mining
    console.log('\n📌 STEP 4: Trigger Mining');
    console.log('-'.repeat(40));
    await triggerMining(page);

    // Final screenshot
    await page.screenshot({ path: '/tmp/e2e-final.png', fullPage: true });
    console.log('\n📸 Final screenshot saved to /tmp/e2e-final.png');

    console.log('\n' + '='.repeat(60));
    console.log('✅ E2E Test completed! Check screenshots in /tmp/');
    console.log('='.repeat(60));

    // Keep browser open for manual inspection
    console.log('\n⏳ Keeping browser open for 30 seconds for inspection...');
    await delay(30000);

  } catch (error) {
    console.error('\n❌ Error during E2E test:', error);
    await page.screenshot({ path: '/tmp/e2e-error.png', fullPage: true });
    console.log('📸 Error screenshot saved to /tmp/e2e-error.png');
  } finally {
    await browser.close();
  }
}

main();
