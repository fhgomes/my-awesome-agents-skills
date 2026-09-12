#!/usr/bin/env node
/**
 * submit-indexing.js
 * Submits URLs for indexing via the Google Indexing API and IndexNow.
 *
 * Usage:
 *   node submit-indexing.js --url="https://your-ghost.com/new-post/"
 *   node submit-indexing.js --url="https://your-ghost.com/new-post/" --google-only
 *   node submit-indexing.js --url="https://your-ghost.com/new-post/" --indexnow-only
 *   node submit-indexing.js --sitemap  # Submits every URL from the sitemap
 *
 * Environment variables:
 *   INDEXNOW_KEY          — IndexNow key (generate one at https://www.bing.com/indexnow)
 *   GOOGLE_INDEXING_KEY   — Google service account JSON (string or path)
 *   GHOST_URL             — Ghost base URL (for the sitemap)
 */

const https = require('https');
const http = require('http');
const crypto = require('crypto');

const GHOST_URL = process.env.GHOST_URL;
const INDEXNOW_KEY = process.env.INDEXNOW_KEY;
const GOOGLE_INDEXING_KEY = process.env.GOOGLE_INDEXING_KEY;

// --- IndexNow ---
async function submitIndexNow(url) {
  if (!INDEXNOW_KEY) {
    console.log('   ⏭️  IndexNow: INDEXNOW_KEY not configured');
    return;
  }

  const host = new URL(url).hostname;
  const apiUrl = `https://api.indexnow.org/IndexNow?url=${encodeURIComponent(url)}&key=${INDEXNOW_KEY}`;

  return new Promise((resolve) => {
    https.get(apiUrl, (res) => {
      if (res.statusCode === 200 || res.statusCode === 202) {
        console.log(`   ✅ IndexNow: Submitted (${res.statusCode})`);
      } else {
        console.log(`   ⚠️  IndexNow: Status ${res.statusCode}`);
      }
      resolve();
    }).on('error', (err) => {
      console.log(`   ❌ IndexNow: ${err.message}`);
      resolve();
    });
  });
}

// --- IndexNow Batch ---
async function submitIndexNowBatch(urls) {
  if (!INDEXNOW_KEY || !GHOST_URL) return;

  const host = new URL(GHOST_URL).hostname;
  const payload = JSON.stringify({
    host,
    key: INDEXNOW_KEY,
    keyLocation: `https://${host}/${INDEXNOW_KEY}.txt`,
    urlList: urls.slice(0, 10000) // max 10k per batch
  });

  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.indexnow.org',
      path: '/IndexNow',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      }
    }, (res) => {
      console.log(`   IndexNow Batch: ${urls.length} URLs → Status ${res.statusCode}`);
      resolve();
    });

    req.on('error', (err) => {
      console.log(`   ❌ IndexNow Batch: ${err.message}`);
      resolve();
    });

    req.write(payload);
    req.end();
  });
}

// --- Google Indexing API (simplified - requires service account setup) ---
async function submitGoogle(url) {
  if (!GOOGLE_INDEXING_KEY) {
    console.log('   ⏭️  Google: GOOGLE_INDEXING_KEY not configured');
    console.log('   💡 Setup: https://developers.google.com/search/apis/indexing-api/v3/quickstart');
    return;
  }

  // Note: Full Google Indexing API requires OAuth2 with service account
  // This is a placeholder — for production, use googleapis npm package
  console.log('   ⚠️  Google Indexing API requires OAuth2 setup with a service account');
  console.log('   💡 Install @googleapis/indexing and configure the service account');
  console.log(`   📋 URL to submit: ${url}`);
}

// --- Sitemap parser ---
async function getUrlsFromSitemap() {
  if (!GHOST_URL) throw new Error('GHOST_URL is required for --sitemap');

  const sitemapUrl = `${GHOST_URL.replace(/\/$/, '')}/sitemap.xml`;

  return new Promise((resolve, reject) => {
    const transport = sitemapUrl.startsWith('https') ? https : http;
    transport.get(sitemapUrl, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        // Simple XML URL extraction (no XML parser needed)
        const urls = [];
        const regex = /<loc>(.*?)<\/loc>/g;
        let match;
        while ((match = regex.exec(data)) !== null) {
          // Skip sub-sitemaps, get actual URLs
          if (!match[1].includes('sitemap') || match[1].includes('.xml')) {
            urls.push(match[1]);
          }
        }

        // If we got sub-sitemaps, we need to fetch those too
        const subSitemaps = urls.filter(u => u.endsWith('.xml'));
        const pageUrls = urls.filter(u => !u.endsWith('.xml'));

        if (subSitemaps.length > 0 && pageUrls.length === 0) {
          // Fetch first sub-sitemap (usually posts)
          Promise.all(subSitemaps.map(sm =>
            new Promise((res2) => {
              transport.get(sm, (res3) => {
                let d = '';
                res3.on('data', c => d += c);
                res3.on('end', () => {
                  const subUrls = [];
                  let m;
                  const r = /<loc>(.*?)<\/loc>/g;
                  while ((m = r.exec(d)) !== null) subUrls.push(m[1]);
                  res2(subUrls);
                });
              }).on('error', () => res2([]));
            })
          )).then(results => resolve(results.flat()));
        } else {
          resolve(pageUrls);
        }
      });
    }).on('error', reject);
  });
}

// --- CLI ---
function parseArgs(args) {
  const opts = {};
  for (const arg of args) {
    if (arg.startsWith('--')) {
      const [key, ...v] = arg.slice(2).split('=');
      opts[key] = v.join('=') || true;
    }
  }
  return opts;
}

// --- Main ---
async function main() {
  const opts = parseArgs(process.argv.slice(2));

  if (opts.sitemap) {
    console.log('🗺️  Submitting sitemap URLs...');
    const urls = await getUrlsFromSitemap();
    console.log(`   Found ${urls.length} URLs`);

    // IndexNow batch
    await submitIndexNowBatch(urls);

    // Google one by one (API limit)
    if (GOOGLE_INDEXING_KEY) {
      for (const url of urls.slice(0, 200)) { // Google daily limit ~200
        await submitGoogle(url);
      }
    }
    return;
  }

  if (!opts.url) {
    console.log('Usage: node submit-indexing.js --url="https://..." [--google-only] [--indexnow-only] [--sitemap]');
    process.exit(0);
  }

  console.log(`🔗 Submitting: ${opts.url}`);

  if (!opts['google-only']) {
    await submitIndexNow(opts.url);
  }

  if (!opts['indexnow-only']) {
    await submitGoogle(opts.url);
  }

  console.log('✅ Submission complete');
}

main().catch(err => {
  console.error('💥', err.message);
  process.exit(1);
});
