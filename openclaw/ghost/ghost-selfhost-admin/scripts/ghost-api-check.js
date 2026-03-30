#!/usr/bin/env node
/**
 * ghost-api-check.js
 * Verifica conexão com Ghost Admin API e lista capabilities disponíveis.
 * 
 * Uso: GHOST_URL=https://meu-ghost.com GHOST_ADMIN_API_KEY=id:secret node ghost-api-check.js
 */

const crypto = require('crypto');
const https = require('https');
const http = require('http');
const url = require('url');

// --- Config ---
const GHOST_URL = process.env.GHOST_URL;
const GHOST_ADMIN_API_KEY = process.env.GHOST_ADMIN_API_KEY;

if (!GHOST_URL || !GHOST_ADMIN_API_KEY) {
  console.error('❌ Variáveis obrigatórias não definidas:');
  if (!GHOST_URL) console.error('   - GHOST_URL (ex: https://meu-ghost.com)');
  if (!GHOST_ADMIN_API_KEY) console.error('   - GHOST_ADMIN_API_KEY (ex: id:secret)');
  process.exit(1);
}

// --- JWT Generation ---
function generateGhostJWT(apiKey) {
  const [id, secret] = apiKey.split(':');
  if (!id || !secret) {
    throw new Error('GHOST_ADMIN_API_KEY deve estar no formato id:secret');
  }

  const header = Buffer.from(JSON.stringify({
    alg: 'HS256',
    typ: 'JWT',
    kid: id
  })).toString('base64url');

  const now = Math.floor(Date.now() / 1000);
  const payload = Buffer.from(JSON.stringify({
    iat: now,
    exp: now + 300, // 5 min
    aud: '/admin/'
  })).toString('base64url');

  const signature = crypto
    .createHmac('sha256', Buffer.from(secret, 'hex'))
    .update(`${header}.${payload}`)
    .digest('base64url');

  return `${header}.${payload}.${signature}`;
}

// --- HTTP Request ---
function ghostGet(endpoint) {
  return new Promise((resolve, reject) => {
    const token = generateGhostJWT(GHOST_ADMIN_API_KEY);
    const fullUrl = `${GHOST_URL.replace(/\/$/, '')}/ghost/api/admin${endpoint}`;
    const parsed = new URL(fullUrl);
    const transport = parsed.protocol === 'https:' ? https : http;

    const options = {
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: {
        'Authorization': `Ghost ${token}`,
        'Accept-Version': 'v5.0',
        'Content-Type': 'application/json'
      }
    };

    const req = transport.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.end();
  });
}

// --- Main ---
async function main() {
  console.log('🔍 Ghost Admin API Health Check');
  console.log(`   URL: ${GHOST_URL}`);
  console.log('');

  // 1. Site info
  try {
    const site = await ghostGet('/site/');
    console.log('✅ Conexão OK');
    console.log(`   Título: ${site.data.site?.title || 'N/A'}`);
    console.log(`   Versão: ${site.data.site?.version || 'N/A'}`);
    console.log(`   URL: ${site.data.site?.url || 'N/A'}`);
    console.log('');
  } catch (err) {
    console.error('❌ Falha na conexão:', err.message);
    process.exit(1);
  }

  // 2. Test endpoints
  const endpoints = [
    { name: 'Posts', path: '/posts/?limit=1' },
    { name: 'Pages', path: '/pages/?limit=1' },
    { name: 'Tags', path: '/tags/?limit=1' },
    { name: 'Users', path: '/users/?limit=1' },
    { name: 'Members', path: '/members/?limit=1' },
    { name: 'Newsletters', path: '/newsletters/?limit=1' },
    { name: 'Tiers', path: '/tiers/?limit=1' },
    { name: 'Offers', path: '/offers/?limit=1' },
    { name: 'Themes', path: '/themes/' },
  ];

  console.log('📋 Endpoints disponíveis:');
  for (const ep of endpoints) {
    try {
      const result = await ghostGet(ep.path);
      const resourceKey = Object.keys(result.data).find(k => k !== 'meta');
      const count = result.data.meta?.pagination?.total 
        || (Array.isArray(result.data[resourceKey]) ? result.data[resourceKey].length : '?');
      console.log(`   ✅ ${ep.name.padEnd(12)} — ${count} items`);
    } catch (err) {
      console.log(`   ⚠️  ${ep.name.padEnd(12)} — ${err.message.substring(0, 50)}`);
    }
  }

  // 3. Active theme
  try {
    const themes = await ghostGet('/themes/');
    const active = themes.data.themes?.find(t => t.active);
    if (active) {
      console.log('');
      console.log(`🎨 Tema ativo: ${active.name} (v${active.package?.version || '?'})`);
    }
  } catch (err) {
    // skip
  }

  console.log('');
  console.log('✅ Health check completo.');
}

main().catch(err => {
  console.error('💥 Erro inesperado:', err.message);
  process.exit(1);
});
