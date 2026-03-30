#!/usr/bin/env node
/**
 * ghost-api-check.js
 * Ghost Admin API health check — verifies connection and lists capabilities.
 *
 * Usage:
 *   GHOST_URL=https://your-ghost.com GHOST_ADMIN_API_KEY=id:secret node ghost-api-check.js
 */

const { requireConfig, apiRequest, GHOST_URL } = require('../lib/ghost-api');
requireConfig();

async function main() {
  console.log('🔍 Ghost Admin API Health Check');
  console.log(`   URL: ${GHOST_URL}`);
  console.log('');

  // 1. Site info
  try {
    const site = await apiRequest('GET', '/site/');
    console.log('✅ Connection OK');
    console.log(`   Title:   ${site.site?.title || 'N/A'}`);
    console.log(`   Version: ${site.site?.version || 'N/A'}`);
    console.log(`   URL:     ${site.site?.url || 'N/A'}`);
    console.log('');
  } catch (err) {
    console.error('❌ Connection failed:', err.message || JSON.stringify(err));
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

  console.log('📋 Available endpoints:');
  for (const ep of endpoints) {
    try {
      const result = await apiRequest('GET', ep.path);
      const resourceKey = Object.keys(result).find(k => k !== 'meta');
      const count = result.meta?.pagination?.total
        || (Array.isArray(result[resourceKey]) ? result[resourceKey].length : '?');
      console.log(`   ✅ ${ep.name.padEnd(12)} — ${count} items`);
    } catch (err) {
      const msg = err.message || JSON.stringify(err);
      console.log(`   ⚠️  ${ep.name.padEnd(12)} — ${msg.substring(0, 50)}`);
    }
  }

  // 3. Active theme
  try {
    const themes = await apiRequest('GET', '/themes/');
    const active = themes.themes?.find(t => t.active);
    if (active) {
      console.log('');
      console.log(`🎨 Active theme: ${active.name} (v${active.package?.version || '?'})`);
    }
  } catch { /* skip */ }

  console.log('');
  console.log('✅ Health check complete.');
}

main().catch(err => {
  console.error('💥 Unexpected error:', err.message);
  process.exit(1);
});
