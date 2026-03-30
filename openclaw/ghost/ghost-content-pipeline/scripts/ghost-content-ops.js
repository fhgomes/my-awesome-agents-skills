#!/usr/bin/env node
/**
 * ghost-content-ops.js
 * Operações de conteúdo no Ghost via Admin API.
 * Reutiliza a lógica JWT do ghost-selfhost-admin.
 * 
 * Uso:
 *   node ghost-content-ops.js posts list [--options]
 *   node ghost-content-ops.js posts create --json='{...}'
 *   node ghost-content-ops.js posts update --id=xxx --json='{...}'
 *   node ghost-content-ops.js posts search --query="texto"
 *   node ghost-content-ops.js posts bulk-tag --filter="..." --add-tag="tag-name"
 *   node ghost-content-ops.js posts oldest-updated --status=published
 *   node ghost-content-ops.js images upload --file=/path/to/image.webp
 *   node ghost-content-ops.js posts export --output=/tmp/export.json
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

// --- HTTP ---
function apiRequest(method, endpoint, body = null) {
  return new Promise((resolve, reject) => {
    const fullUrl = `${GHOST_URL.replace(/\/$/, '')}/ghost/api/admin${endpoint}`;
    const parsed = new URL(fullUrl);
    const transport = parsed.protocol === 'https:' ? https : http;

    const headers = {
      'Authorization': `Ghost ${generateJWT()}`,
      'Accept-Version': 'v5.0',
      'Content-Type': 'application/json'
    };

    const options = {
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname + (parsed.search || ''),
      method,
      headers
    };

    if (body) headers['Content-Length'] = Buffer.byteLength(body);

    const req = transport.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode >= 200 && res.statusCode < 300) resolve(parsed);
          else reject({ status: res.statusCode, errors: parsed.errors || parsed });
        } catch {
          resolve(data);
        }
      });
    });

    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

function uploadFile(endpoint, filePath) {
  return new Promise((resolve, reject) => {
    const boundary = '----Upload' + crypto.randomBytes(8).toString('hex');
    const fileName = path.basename(filePath);
    const fileContent = fs.readFileSync(filePath);
    const ext = path.extname(fileName).toLowerCase();
    const mimeTypes = {
      '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
      '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml'
    };

    const prefix = Buffer.from(
      `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${fileName}"\r\nContent-Type: ${mimeTypes[ext] || 'application/octet-stream'}\r\n\r\n`
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
      res.on('end', () => resolve(JSON.parse(data)));
    });

    req.on('error', reject);
    req.write(bodyBuffer);
    req.end();
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

// --- Browse all pages ---
async function browseAll(resource, filter = '', fields = '') {
  let allItems = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const params = [`page=${page}`, 'limit=50'];
    if (filter) params.push(`filter=${encodeURIComponent(filter)}`);
    if (fields) params.push(`fields=${fields}`);
    
    const result = await apiRequest('GET', `/${resource}/?${params.join('&')}`);
    const items = result[resource] || [];
    allItems = allItems.concat(items);
    totalPages = result.meta?.pagination?.pages || 1;
    page++;
  }

  return allItems;
}

// --- Main ---
async function main() {
  const [,, resource, action, ...rest] = process.argv;
  const opts = parseArgs(rest);

  if (!resource || !action) {
    console.log('Uso: node ghost-content-ops.js <resource> <action> [--options]');
    console.log('');
    console.log('Ações especiais:');
    console.log('  posts search --query="texto"         Buscar posts por título');
    console.log('  posts oldest-updated                 Post mais antigo (pra content improver)');
    console.log('  posts bulk-tag --filter=... --add-tag=name  Adicionar tag em massa');
    console.log('  posts export --output=file.json      Exportar todos os posts');
    console.log('  posts stats                          Estatísticas do conteúdo');
    console.log('  images upload --file=/path/to/img    Upload de imagem');
    process.exit(0);
  }

  try {
    switch (`${resource}:${action}`) {
      
      // --- Posts: search ---
      case 'posts:search': {
        if (!opts.query) throw new Error('--query é obrigatório');
        const posts = await browseAll('posts', '', 'id,title,slug,status,published_at,updated_at');
        const query = opts.query.toLowerCase();
        const matches = posts.filter(p => 
          p.title?.toLowerCase().includes(query) || p.slug?.includes(query)
        );
        console.log(`🔍 ${matches.length} posts encontrados para "${opts.query}":`);
        matches.forEach(p => {
          console.log(`   [${p.status}] ${p.title} → /${p.slug}/`);
        });
        break;
      }

      // --- Posts: oldest updated ---
      case 'posts:oldest-updated': {
        const status = opts.status || 'published';
        const result = await apiRequest('GET', 
          `/posts/?filter=status:${status}&order=updated_at+asc&limit=1&include=tags`
        );
        const post = result.posts?.[0];
        if (post) {
          console.log(JSON.stringify({
            id: post.id,
            title: post.title,
            slug: post.slug,
            updated_at: post.updated_at,
            published_at: post.published_at,
            url: `${GHOST_URL}/${post.slug}/`,
            tags: post.tags?.map(t => t.name),
            word_count: post.html?.split(/\s+/).length || 0,
            has_feature_image: !!post.feature_image,
            has_meta_description: !!post.meta_description,
            has_custom_excerpt: !!post.custom_excerpt
          }, null, 2));
        } else {
          console.log('Nenhum post encontrado');
        }
        break;
      }

      // --- Posts: bulk tag ---
      case 'posts:bulk-tag': {
        if (!opts['add-tag']) throw new Error('--add-tag é obrigatório');
        const filter = opts.filter || '';
        const posts = await browseAll('posts', filter, 'id,title,updated_at');
        
        // Get or create tag
        let tagResult = await apiRequest('GET', `/tags/slug/${opts['add-tag']}/`).catch(() => null);
        let tagObj;
        if (!tagResult) {
          const created = await apiRequest('POST', '/tags/', 
            JSON.stringify({ tags: [{ name: opts['add-tag'] }] })
          );
          tagObj = created.tags[0];
          console.log(`🏷️  Tag "${opts['add-tag']}" criada`);
        } else {
          tagObj = tagResult.tags[0];
        }

        console.log(`📦 Atualizando ${posts.length} posts com tag "${opts['add-tag']}"...`);
        let updated = 0;
        for (const post of posts) {
          try {
            // Get full post with tags
            const full = await apiRequest('GET', `/posts/${post.id}/?include=tags`);
            const currentTags = full.posts[0].tags || [];
            
            if (currentTags.some(t => t.slug === opts['add-tag'])) continue;

            const tagSlugs = [...currentTags.map(t => ({ slug: t.slug })), { slug: tagObj.slug }];
            await apiRequest('PUT', `/posts/${post.id}/`, JSON.stringify({
              posts: [{ tags: tagSlugs, updated_at: full.posts[0].updated_at }]
            }));
            updated++;
            process.stdout.write(`\r   ${updated}/${posts.length}`);
          } catch (err) {
            console.error(`\n   ⚠️ Erro em "${post.title}": ${JSON.stringify(err)}`);
          }
        }
        console.log(`\n✅ ${updated} posts atualizados`);
        break;
      }

      // --- Posts: export ---
      case 'posts:export': {
        const output = opts.output || `/tmp/ghost-export-${Date.now()}.json`;
        const posts = await browseAll('posts', '', '');
        fs.writeFileSync(output, JSON.stringify({ posts, exported_at: new Date().toISOString() }, null, 2));
        console.log(`✅ ${posts.length} posts exportados para ${output}`);
        break;
      }

      // --- Posts: stats ---
      case 'posts:stats': {
        const [published, drafts, scheduled] = await Promise.all([
          apiRequest('GET', '/posts/?filter=status:published&limit=1'),
          apiRequest('GET', '/posts/?filter=status:draft&limit=1'),
          apiRequest('GET', '/posts/?filter=status:scheduled&limit=1'),
        ]);
        
        const members = await apiRequest('GET', '/members/?limit=1').catch(() => null);
        const tags = await apiRequest('GET', '/tags/?limit=1').catch(() => null);
        const newsletters = await apiRequest('GET', '/newsletters/?limit=1').catch(() => null);

        console.log('📊 Ghost Content Stats:');
        console.log(`   Published:   ${published.meta?.pagination?.total || 0}`);
        console.log(`   Drafts:      ${drafts.meta?.pagination?.total || 0}`);
        console.log(`   Scheduled:   ${scheduled.meta?.pagination?.total || 0}`);
        console.log(`   Tags:        ${tags?.meta?.pagination?.total || '?'}`);
        console.log(`   Members:     ${members?.meta?.pagination?.total || '?'}`);
        console.log(`   Newsletters: ${newsletters?.meta?.pagination?.total || '?'}`);
        break;
      }

      // --- Images upload ---
      case 'images:upload': {
        if (!opts.file) throw new Error('--file é obrigatório');
        const result = await uploadFile('/images/upload/', opts.file);
        console.log(JSON.stringify(result, null, 2));
        break;
      }

      // --- Generic CRUD (fallback) ---
      default: {
        const plural = resource.endsWith('s') ? resource : resource + 's';
        const params = [];
        if (opts.limit) params.push(`limit=${opts.limit}`);
        if (opts.page) params.push(`page=${opts.page}`);
        if (opts.filter) params.push(`filter=${encodeURIComponent(opts.filter)}`);
        if (opts.order) params.push(`order=${encodeURIComponent(opts.order)}`);
        if (opts.include) params.push(`include=${opts.include}`);
        if (opts.fields) params.push(`fields=${opts.fields}`);
        if (opts.status) params.push(`filter=status:${opts.status}`);
        const qs = params.length ? '?' + params.join('&') : '';

        let result;
        switch (action) {
          case 'list':
            result = await apiRequest('GET', `/${plural}/${qs}`);
            break;
          case 'get':
            result = await apiRequest('GET', `/${plural}/${opts.id || opts.slug ? 'slug/' + opts.slug : ''}/`);
            break;
          case 'create':
            result = await apiRequest('POST', `/${plural}/`, 
              JSON.stringify({ [plural]: [JSON.parse(opts.json)] }));
            break;
          case 'update':
            if (!opts.id) throw new Error('--id é obrigatório');
            const updateData = JSON.parse(opts.json);
            if (!updateData.updated_at) {
              const current = await apiRequest('GET', `/${plural}/${opts.id}/`);
              updateData.updated_at = current[plural]?.[0]?.updated_at;
            }
            result = await apiRequest('PUT', `/${plural}/${opts.id}/`,
              JSON.stringify({ [plural]: [updateData] }));
            break;
          case 'delete':
            await apiRequest('DELETE', `/${plural}/${opts.id}/`);
            console.log('✅ Deletado');
            return;
          default:
            throw new Error(`Ação "${action}" não reconhecida`);
        }
        console.log(JSON.stringify(result, null, 2));
      }
    }
  } catch (err) {
    console.error('❌', JSON.stringify(err, null, 2));
    process.exit(1);
  }
}

main();
