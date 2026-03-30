/**
 * ghost-api.js — Shared Ghost Admin API utilities
 *
 * Provides JWT generation, HTTP client, file upload, and CLI parsing
 * for all Ghost automation scripts.
 *
 * Usage:
 *   const { generateJWT, apiRequest, uploadFile, parseArgs, GHOST_URL } = require('../lib/ghost-api');
 */

const crypto = require('crypto');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const GHOST_URL = process.env.GHOST_URL;
const GHOST_ADMIN_API_KEY = process.env.GHOST_ADMIN_API_KEY;

function requireConfig() {
  if (!GHOST_URL || !GHOST_ADMIN_API_KEY) {
    console.error('❌ GHOST_URL and GHOST_ADMIN_API_KEY are required');
    process.exit(1);
  }
}

function generateJWT() {
  const [id, secret] = GHOST_ADMIN_API_KEY.split(':');
  if (!id || !secret) throw new Error('GHOST_ADMIN_API_KEY must be in id:secret format');

  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT', kid: id })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const payload = Buffer.from(JSON.stringify({ iat: now, exp: now + 300, aud: '/admin/' })).toString('base64url');
  const sig = crypto.createHmac('sha256', Buffer.from(secret, 'hex')).update(`${header}.${payload}`).digest('base64url');
  return `${header}.${payload}.${sig}`;
}

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
    if (body && typeof body === 'string') {
      headers['Content-Length'] = Buffer.byteLength(body);
    }

    const req = transport.request({
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname + (parsed.search || ''),
      method,
      headers
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (res.statusCode >= 200 && res.statusCode < 300) resolve(json);
          else reject({ status: res.statusCode, errors: json.errors || json });
        } catch {
          if (res.statusCode >= 200 && res.statusCode < 300) resolve(data);
          else reject({ status: res.statusCode, body: data });
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

    const req = transport.request({
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
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { resolve(data); }
      });
    });

    req.on('error', reject);
    req.write(bodyBuffer);
    req.end();
  });
}

async function browseAll(resource, filter = '', fields = '') {
  let allItems = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const params = [`page=${page}`, 'limit=50'];
    if (filter) params.push(`filter=${encodeURIComponent(filter)}`);
    if (fields) params.push(`fields=${fields}`);

    const result = await apiRequest('GET', `/${resource}/?${params.join('&')}`);
    allItems = allItems.concat(result[resource] || []);
    totalPages = result.meta?.pagination?.pages || 1;
    page++;
  }

  return allItems;
}

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

module.exports = {
  GHOST_URL,
  GHOST_ADMIN_API_KEY,
  requireConfig,
  generateJWT,
  apiRequest,
  uploadFile,
  browseAll,
  parseArgs
};
