#!/usr/bin/env node
/**
 * ghost-admin-client.js
 * Cliente wrapper para Ghost Admin API com suporte a todas as operações CRUD.
 * 
 * Uso:
 *   node ghost-admin-client.js <resource> <action> [options]
 * 
 * Exemplos:
 *   node ghost-admin-client.js posts list --limit=5 --status=published
 *   node ghost-admin-client.js posts get --id=abc123
 *   node ghost-admin-client.js posts create --json='{"title":"Novo Post","html":"<p>Conteudo</p>"}'
 *   node ghost-admin-client.js settings get
 *   node ghost-admin-client.js settings update --json='{"title":"Meu Blog","description":"desc"}'
 *   node ghost-admin-client.js images upload --file=/path/to/image.jpg
 *   node ghost-admin-client.js themes upload --file=/path/to/theme.zip
 *   node ghost-admin-client.js themes activate --name=casper
 *   node ghost-admin-client.js site info
 */

const crypto = require('crypto');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

// --- Config ---
const GHOST_URL = process.env.GHOST_URL;
const GHOST_ADMIN_API_KEY = process.env.GHOST_ADMIN_API_KEY;

if (!GHOST_URL || !GHOST_ADMIN_API_KEY) {
  console.error('❌ GHOST_URL e GHOST_ADMIN_API_KEY são obrigatórios');
  process.exit(1);
}

// --- JWT ---
function generateJWT() {
  const [id, secret] = GHOST_ADMIN_API_KEY.split(':');
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT', kid: id })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const payload = Buffer.from(JSON.stringify({ iat: now, exp: now + 300, aud: '/admin/' })).toString('base64url');
  const sig = crypto.createHmac('sha256', Buffer.from(secret, 'hex')).update(`${header}.${payload}`).digest('base64url');
  return `${header}.${payload}.${sig}`;
}

// --- HTTP helpers ---
function apiRequest(method, endpoint, body = null, contentType = 'application/json') {
  return new Promise((resolve, reject) => {
    const fullUrl = `${GHOST_URL.replace(/\/$/, '')}/ghost/api/admin${endpoint}`;
    const parsed = new URL(fullUrl);
    const transport = parsed.protocol === 'https:' ? https : http;

    const headers = {
      'Authorization': `Ghost ${generateJWT()}`,
      'Accept-Version': 'v5.0',
    };
    if (contentType && !contentType.includes('multipart')) {
      headers['Content-Type'] = contentType;
    }

    const options = {
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname + (parsed.search || ''),
      method,
      headers
    };

    if (body && typeof body === 'string') {
      headers['Content-Length'] = Buffer.byteLength(body);
    }

    const req = transport.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(parsed);
          } else {
            reject({ status: res.statusCode, errors: parsed.errors || parsed });
          }
        } catch {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data);
          } else {
            reject({ status: res.statusCode, body: data });
          }
        }
      });
    });

    req.on('error', reject);
    if (body) req.write(typeof body === 'string' ? body : body);
    req.end();
  });
}

function uploadFile(endpoint, filePath, fieldName = 'file') {
  return new Promise((resolve, reject) => {
    const boundary = '----GhostUpload' + crypto.randomBytes(8).toString('hex');
    const fileName = path.basename(filePath);
    const fileContent = fs.readFileSync(filePath);
    
    const ext = path.extname(fileName).toLowerCase();
    const mimeTypes = {
      '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
      '.gif': 'image/gif', '.svg': 'image/svg+xml', '.webp': 'image/webp',
      '.zip': 'application/zip', '.ico': 'image/x-icon'
    };
    const contentType = mimeTypes[ext] || 'application/octet-stream';

    const prefix = Buffer.from(
      `--${boundary}\r\n` +
      `Content-Disposition: form-data; name="${fieldName}"; filename="${fileName}"\r\n` +
      `Content-Type: ${contentType}\r\n\r\n`
    );
    const suffix = Buffer.from(`\r\n--${boundary}--\r\n`);
    const bodyBuffer = Buffer.concat([prefix, fileContent, suffix]);

    const fullUrl = `${GHOST_URL.replace(/\/$/, '')}/ghost/api/admin${endpoint}`;
    const parsed = new URL(fullUrl);
    const transport = parsed.protocol === 'https:' ? https : http;

    const options = {
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname,
      method: 'POST',
      headers: {
        'Authorization': `Ghost ${generateJWT()}`,
        'Accept-Version': 'v5.0',
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': bodyBuffer.length
      }
    };

    const req = transport.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve(parsed);
        } catch {
          resolve(data);
        }
      });
    });

    req.on('error', reject);
    req.write(bodyBuffer);
    req.end();
  });
}

// --- CLI parsing ---
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

// --- Main ---
async function main() {
  const [,, resource, action, ...rest] = process.argv;
  const opts = parseArgs(rest);

  if (!resource || !action) {
    console.log('Uso: node ghost-admin-client.js <resource> <action> [--options]');
    console.log('');
    console.log('Resources: posts, pages, tags, users, members, newsletters, tiers, offers, webhooks, themes, images, settings, site');
    console.log('Actions:   list, get, create, update, delete, upload, activate, info');
    process.exit(0);
  }

  try {
    let result;

    switch (`${resource}:${action}`) {
      // --- Site ---
      case 'site:info':
        result = await apiRequest('GET', '/site/');
        break;

      // --- Settings ---
      case 'settings:get':
        result = await apiRequest('GET', '/settings/');
        break;
      case 'settings:update':
        if (!opts.json) throw new Error('--json é obrigatório para update');
        const settings = JSON.parse(opts.json);
        const settingsPayload = { settings: Object.entries(settings).map(([key, value]) => ({ key, value })) };
        result = await apiRequest('PUT', '/settings/', JSON.stringify(settingsPayload));
        break;

      // --- Images ---
      case 'images:upload':
        if (!opts.file) throw new Error('--file é obrigatório para upload');
        result = await uploadFile('/images/upload/', opts.file, 'file');
        break;

      // --- Themes ---
      case 'themes:list':
        result = await apiRequest('GET', '/themes/');
        break;
      case 'themes:upload':
        if (!opts.file) throw new Error('--file é obrigatório para upload de tema');
        result = await uploadFile('/themes/upload/', opts.file, 'file');
        break;
      case 'themes:activate':
        if (!opts.name) throw new Error('--name é obrigatório para ativar tema');
        result = await apiRequest('PUT', `/themes/${opts.name}/activate/`);
        break;

      // --- Generic CRUD ---
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
            if (!opts.id && !opts.slug) throw new Error('--id ou --slug é obrigatório');
            const identifier = opts.slug ? `slug/${opts.slug}` : opts.id;
            result = await apiRequest('GET', `/${plural}/${identifier}/`);
            break;
          case 'create':
            if (!opts.json) throw new Error('--json é obrigatório');
            result = await apiRequest('POST', `/${plural}/`, JSON.stringify({ [plural]: [JSON.parse(opts.json)] }));
            break;
          case 'update':
            if (!opts.id || !opts.json) throw new Error('--id e --json são obrigatórios');
            const updateData = JSON.parse(opts.json);
            // Ghost requires updated_at for conflict detection
            if (!updateData.updated_at) {
              const current = await apiRequest('GET', `/${plural}/${opts.id}/`);
              updateData.updated_at = current[plural]?.[0]?.updated_at;
            }
            result = await apiRequest('PUT', `/${plural}/${opts.id}/`, JSON.stringify({ [plural]: [updateData] }));
            break;
          case 'delete':
            if (!opts.id) throw new Error('--id é obrigatório');
            result = await apiRequest('DELETE', `/${plural}/${opts.id}/`);
            console.log('✅ Deletado com sucesso');
            return;
          default:
            throw new Error(`Ação desconhecida: ${action}`);
        }
      }
    }

    console.log(JSON.stringify(result, null, 2));
  } catch (err) {
    console.error('❌ Erro:', JSON.stringify(err, null, 2));
    process.exit(1);
  }
}

main();
