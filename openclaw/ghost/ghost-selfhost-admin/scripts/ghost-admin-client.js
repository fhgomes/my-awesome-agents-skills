#!/usr/bin/env node
/**
 * ghost-admin-client.js
 * Ghost Admin API client — settings, themes, images, and generic CRUD.
 *
 * Usage:
 *   node ghost-admin-client.js <resource> <action> [--options]
 *
 * Examples:
 *   node ghost-admin-client.js settings get
 *   node ghost-admin-client.js settings update --json='{"title":"My Blog","description":"desc"}'
 *   node ghost-admin-client.js posts list --limit=5 --status=published
 *   node ghost-admin-client.js posts get --id=abc123
 *   node ghost-admin-client.js posts create --json='{"title":"New Post","html":"<p>Content</p>"}'
 *   node ghost-admin-client.js images upload --file=/path/to/image.jpg
 *   node ghost-admin-client.js themes upload --file=/path/to/theme.zip
 *   node ghost-admin-client.js themes activate --name=casper
 *   node ghost-admin-client.js site info
 */

const { requireConfig, apiRequest, uploadFile, parseArgs } = require('../lib/ghost-api');
requireConfig();

async function main() {
  const [,, resource, action, ...rest] = process.argv;
  const opts = parseArgs(rest);

  if (!resource || !action) {
    console.log('Usage: node ghost-admin-client.js <resource> <action> [--options]');
    console.log('');
    console.log('Resources: posts, pages, tags, users, members, newsletters, tiers, offers, webhooks, themes, images, settings, site');
    console.log('Actions:   list, get, create, update, delete, upload, activate, info');
    process.exit(0);
  }

  try {
    let result;

    switch (`${resource}:${action}`) {
      case 'site:info':
        result = await apiRequest('GET', '/site/');
        break;

      case 'settings:get':
        result = await apiRequest('GET', '/settings/');
        break;
      case 'settings:update':
        // NOTE: Ghost 5.x returns 501 for PUT /settings/ with Integration API keys.
        // Settings write requires session auth (ghost-setup.py) or Playwright.
        console.error('⚠️  Settings update is NOT supported via API key (Ghost 5.x returns 501).');
        console.error('   Use ghost-setup.py (session auth) or ghost-playwright-admin.js instead.');
        process.exit(1);
        break;

      case 'images:upload':
        if (!opts.file) throw new Error('--file is required for upload');
        result = await uploadFile('/images/upload/', opts.file, 'file');
        break;

      case 'themes:list':
        result = await apiRequest('GET', '/themes/');
        break;
      case 'themes:upload':
        if (!opts.file) throw new Error('--file is required for theme upload');
        result = await uploadFile('/themes/upload/', opts.file, 'file');
        break;
      case 'themes:activate':
        if (!opts.name) throw new Error('--name is required to activate theme');
        result = await apiRequest('PUT', `/themes/${opts.name}/activate/`);
        break;

      default: {
        const plural = resource.endsWith('s') ? resource : resource + 's';
        const queryParams = [];
        if (opts.limit) queryParams.push(`limit=${opts.limit}`);
        if (opts.page) queryParams.push(`page=${opts.page}`);
        if (opts.status) queryParams.push(`filter=status:${opts.status}`);
        if (opts.filter) queryParams.push(`filter=${encodeURIComponent(opts.filter)}`);
        if (opts.include) queryParams.push(`include=${opts.include}`);
        if (opts.fields) queryParams.push(`fields=${opts.fields}`);
        if (opts.order) queryParams.push(`order=${encodeURIComponent(opts.order)}`);
        const qs = queryParams.length ? '?' + queryParams.join('&') : '';

        switch (action) {
          case 'list':
            result = await apiRequest('GET', `/${plural}/${qs}`);
            break;
          case 'get':
            if (!opts.id && !opts.slug) throw new Error('--id or --slug is required');
            const identifier = opts.slug ? `slug/${opts.slug}` : opts.id;
            result = await apiRequest('GET', `/${plural}/${identifier}/`);
            break;
          case 'create':
            if (!opts.json) throw new Error('--json is required');
            result = await apiRequest('POST', `/${plural}/`, JSON.stringify({ [plural]: [JSON.parse(opts.json)] }));
            break;
          case 'update':
            if (!opts.id || !opts.json) throw new Error('--id and --json are required');
            const updateData = JSON.parse(opts.json);
            if (!updateData.updated_at) {
              const current = await apiRequest('GET', `/${plural}/${opts.id}/`);
              updateData.updated_at = current[plural]?.[0]?.updated_at;
            }
            result = await apiRequest('PUT', `/${plural}/${opts.id}/`, JSON.stringify({ [plural]: [updateData] }));
            break;
          case 'delete':
            if (!opts.id) throw new Error('--id is required');
            await apiRequest('DELETE', `/${plural}/${opts.id}/`);
            console.log('✅ Deleted');
            return;
          default:
            throw new Error(`Unknown action: ${action}`);
        }
      }
    }

    console.log(JSON.stringify(result, null, 2));
  } catch (err) {
    console.error('❌ Error:', JSON.stringify(err, null, 2));
    process.exit(1);
  }
}

main();
