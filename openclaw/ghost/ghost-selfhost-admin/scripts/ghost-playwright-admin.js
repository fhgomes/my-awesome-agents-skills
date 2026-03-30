#!/usr/bin/env node
/**
 * ghost-playwright-admin.js
 * Automação Playwright para operações Ghost Admin que não têm endpoint na API.
 * 
 * Uso:
 *   node ghost-playwright-admin.js <operation> [--options]
 * 
 * Operações:
 *   login                          — Login e salvar sessão
 *   code-injection --header="..." --footer="..."  — Configurar code injection
 *   navigation --primary='[...]' --secondary='[...]' — Configurar menus
 *   design --json='{"...":"..."}'  — Configurar design settings
 *   portal --json='{"...":"..."}'  — Configurar Portal settings
 *   email --json='{"...":"..."}'   — Configurar email/Mailgun
 *   labs --toggle=feature_name     — Toggle Labs feature
 *   screenshot --page=dashboard    — Screenshot de página admin
 * 
 * Requer: npx playwright install chromium (primeira vez)
 */

const GHOST_URL = process.env.GHOST_URL;
const GHOST_ADMIN_EMAIL = process.env.GHOST_ADMIN_EMAIL;
const GHOST_ADMIN_PASSWORD = process.env.GHOST_ADMIN_PASSWORD;

if (!GHOST_URL || !GHOST_ADMIN_EMAIL || !GHOST_ADMIN_PASSWORD) {
  console.error('❌ Variáveis obrigatórias para Playwright:');
  console.error('   GHOST_URL, GHOST_ADMIN_EMAIL, GHOST_ADMIN_PASSWORD');
  process.exit(1);
}

const ADMIN_URL = `${GHOST_URL.replace(/\/$/, '')}/ghost`;
const STORAGE_STATE = '/tmp/ghost-playwright-session.json';

// --- Helpers ---
function parseArgs(args) {
  const opts = {};
  for (const arg of args) {
    if (arg.startsWith('--')) {
      const [key, ...valParts] = arg.slice(2).split('=');
      opts[key] = valParts.join('=') || true;
    }
  }
  return opts;
}

async function getPlaywright() {
  try {
    return require('playwright');
  } catch {
    console.log('📦 Instalando Playwright...');
    const { execSync } = require('child_process');
    execSync('npx playwright install chromium', { stdio: 'inherit' });
    return require('playwright');
  }
}

async function createBrowser(pw) {
  return pw.chromium.launch({ headless: true });
}

async function loginAndGetContext(browser) {
  const fs = require('fs');
  
  // Try to reuse session
  if (fs.existsSync(STORAGE_STATE)) {
    try {
      const context = await browser.newContext({ storageState: STORAGE_STATE });
      const page = await context.newPage();
      await page.goto(`${ADMIN_URL}/#/dashboard`, { waitUntil: 'networkidle', timeout: 15000 });
      
      // Check if still logged in
      if (!page.url().includes('/signin')) {
        console.log('🔑 Sessão reutilizada');
        return { context, page };
      }
      await context.close();
    } catch {
      // Session expired, continue to fresh login
    }
  }
  
  // Fresh login
  const context = await browser.newContext();
  const page = await context.newPage();
  
  await page.goto(`${ADMIN_URL}/#/signin`, { waitUntil: 'networkidle' });
  await page.fill('input[name="identification"]', GHOST_ADMIN_EMAIL);
  await page.fill('input[name="password"]', GHOST_ADMIN_PASSWORD);
  await page.click('button[type="submit"]');
  
  // Wait for redirect to dashboard
  await page.waitForURL(/\/#\/(dashboard|site)/, { timeout: 15000 });
  console.log('✅ Login realizado');
  
  // Save session
  await context.storageState({ path: STORAGE_STATE });
  
  return { context, page };
}

// --- Operations ---

async function codeInjection(page, opts) {
  console.log('💉 Configurando Code Injection...');
  await page.goto(`${ADMIN_URL}/#/settings/code-injection`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  if (opts.header !== undefined) {
    const headerEditor = page.locator('[data-setting="codeinjection_head"] .CodeMirror');
    if (await headerEditor.count() > 0) {
      await headerEditor.click();
      // Select all and replace
      await page.keyboard.press('Meta+A');
      await page.keyboard.press('Backspace');
      await page.keyboard.type(opts.header);
      console.log('   ✅ Header atualizado');
    } else {
      // Fallback: try textarea
      const textarea = page.locator('#ghost-head');
      if (await textarea.count() > 0) {
        await textarea.fill(opts.header);
        console.log('   ✅ Header atualizado (textarea)');
      }
    }
  }

  if (opts.footer !== undefined) {
    const footerEditor = page.locator('[data-setting="codeinjection_foot"] .CodeMirror');
    if (await footerEditor.count() > 0) {
      await footerEditor.click();
      await page.keyboard.press('Meta+A');
      await page.keyboard.press('Backspace');
      await page.keyboard.type(opts.footer);
      console.log('   ✅ Footer atualizado');
    } else {
      const textarea = page.locator('#ghost-foot');
      if (await textarea.count() > 0) {
        await textarea.fill(opts.footer);
        console.log('   ✅ Footer atualizado (textarea)');
      }
    }
  }

  // Save
  const saveButton = page.locator('button:has-text("Save")');
  if (await saveButton.isEnabled()) {
    await saveButton.click();
    await page.waitForTimeout(1000);
    console.log('   ✅ Salvo com sucesso');
  }
}

async function configureNavigation(page, opts) {
  console.log('🧭 Configurando Navigation...');
  await page.goto(`${ADMIN_URL}/#/settings/navigation`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  if (opts.primary) {
    const items = JSON.parse(opts.primary);
    console.log(`   Configurando ${items.length} itens no menu primário...`);
    // Note: Ghost navigation UI is complex - this is a simplified version
    // For production, inspect the actual DOM structure of your Ghost version
    console.log('   ⚠️  Configuração de navigation requer interação manual específica por versão');
    console.log('   💡 Use a API de settings com o campo "navigation" se disponível');
  }

  if (opts.secondary) {
    const items = JSON.parse(opts.secondary);
    console.log(`   Configurando ${items.length} itens no menu secundário...`);
    console.log('   ⚠️  Mesmo aviso acima');
  }
}

async function configureDesign(page, opts) {
  console.log('🎨 Configurando Design...');
  await page.goto(`${ADMIN_URL}/#/settings/design`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  if (opts.json) {
    const settings = JSON.parse(opts.json);
    console.log(`   Aplicando ${Object.keys(settings).length} configurações de design...`);
    // Design settings are theme-specific and vary heavily
    // This provides the framework - specific selectors need to be adapted per theme
    for (const [key, value] of Object.entries(settings)) {
      console.log(`   🔧 ${key}: ${value}`);
    }
    console.log('   ⚠️  Design settings são específicos por tema - adapte os seletores');
  }
}

async function takeScreenshot(page, opts) {
  const pageMap = {
    dashboard: '/#/dashboard',
    posts: '/#/posts',
    pages: '/#/pages',
    members: '/#/members',
    settings: '/#/settings',
    design: '/#/settings/design',
    'code-injection': '/#/settings/code-injection',
    navigation: '/#/settings/navigation',
    labs: '/#/settings/labs',
  };

  const target = pageMap[opts.page] || `/#/${opts.page}`;
  console.log(`📸 Screenshot de ${opts.page}...`);
  
  await page.goto(`${ADMIN_URL}${target}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  const outputPath = opts.output || `/tmp/ghost-screenshot-${opts.page}-${Date.now()}.png`;
  await page.screenshot({ path: outputPath, fullPage: true });
  console.log(`   ✅ Salvo em: ${outputPath}`);
}

// --- Main ---
async function main() {
  const [,, operation, ...rest] = process.argv;
  const opts = parseArgs(rest);

  if (!operation) {
    console.log('Uso: node ghost-playwright-admin.js <operation> [--options]');
    console.log('Operações: login, code-injection, navigation, design, portal, email, labs, screenshot');
    process.exit(0);
  }

  const pw = await getPlaywright();
  const browser = await createBrowser(pw);

  try {
    const { context, page } = await loginAndGetContext(browser);

    switch (operation) {
      case 'login':
        console.log('✅ Login testado com sucesso');
        break;
      case 'code-injection':
        await codeInjection(page, opts);
        break;
      case 'navigation':
        await configureNavigation(page, opts);
        break;
      case 'design':
        await configureDesign(page, opts);
        break;
      case 'screenshot':
        await takeScreenshot(page, opts);
        break;
      default:
        console.log(`⚠️  Operação '${operation}' ainda não implementada.`);
        console.log('   Operações disponíveis: login, code-injection, navigation, design, screenshot');
    }

    await context.close();
  } finally {
    await browser.close();
  }
}

main().catch(err => {
  console.error('💥 Erro:', err.message);
  process.exit(1);
});
