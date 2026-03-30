#!/usr/bin/env node
/**
 * ghost-content-ops.js
 * Ghost content operations — search, bulk-tag, export, stats, and generic CRUD.
 *
 * Usage:
 *   node ghost-content-ops.js posts list [--options]
 *   node ghost-content-ops.js posts create --json='{...}'
 *   node ghost-content-ops.js posts search --query="text"
 *   node ghost-content-ops.js posts bulk-tag --filter="..." --add-tag="tag-name"
 *   node ghost-content-ops.js posts oldest-updated --status=published
 *   node ghost-content-ops.js posts export --output=/tmp/export.json
 *   node ghost-content-ops.js posts stats
 *   node ghost-content-ops.js images upload --file=/path/to/image.webp
 */

const fs = require('fs');
const { requireConfig, apiRequest, uploadFile, browseAll, parseArgs, GHOST_URL } = require('../../ghost-selfhost-admin/lib/ghost-api');
requireConfig();

async function main() {
  const [,, resource, action, ...rest] = process.argv;
  const opts = parseArgs(rest);

  if (!resource || !action) {
    console.log('Usage: node ghost-content-ops.js <resource> <action> [--options]');
    console.log('');
    console.log('Content-specific actions:');
    console.log('  posts search --query="text"              Search posts by title');
    console.log('  posts oldest-updated                     Oldest post (for content improver)');
    console.log('  posts bulk-tag --filter=... --add-tag=x  Bulk-add tags');
    console.log('  posts export --output=file.json          Export all posts');
    console.log('  posts stats                              Content statistics');
    console.log('  images upload --file=/path/to/img        Upload image');
    process.exit(0);
  }

  try {
    switch (`${resource}:${action}`) {

      case 'posts:search': {
        if (!opts.query) throw new Error('--query is required');
        const posts = await browseAll('posts', '', 'id,title,slug,status,published_at,updated_at');
        const query = opts.query.toLowerCase();
        const matches = posts.filter(p =>
          p.title?.toLowerCase().includes(query) || p.slug?.includes(query)
        );
        console.log(`🔍 ${matches.length} posts found for "${opts.query}":`);
        matches.forEach(p => console.log(`   [${p.status}] ${p.title} → /${p.slug}/`));
        break;
      }

      case 'posts:oldest-updated': {
        const status = opts.status || 'published';
        const result = await apiRequest('GET',
          `/posts/?filter=status:${status}&order=updated_at+asc&limit=1&include=tags`
        );
        const post = result.posts?.[0];
        if (post) {
          console.log(JSON.stringify({
            id: post.id, title: post.title, slug: post.slug,
            updated_at: post.updated_at, published_at: post.published_at,
            url: `${GHOST_URL}/${post.slug}/`,
            tags: post.tags?.map(t => t.name),
            word_count: post.html?.split(/\s+/).length || 0,
            has_feature_image: !!post.feature_image,
            has_meta_description: !!post.meta_description,
            has_custom_excerpt: !!post.custom_excerpt
          }, null, 2));
        } else {
          console.log('No posts found');
        }
        break;
      }

      case 'posts:bulk-tag': {
        if (!opts['add-tag']) throw new Error('--add-tag is required');
        const filter = opts.filter || '';
        const posts = await browseAll('posts', filter, 'id,title,updated_at');

        let tagResult = await apiRequest('GET', `/tags/slug/${opts['add-tag']}/`).catch(() => null);
        let tagObj;
        if (!tagResult) {
          const created = await apiRequest('POST', '/tags/',
            JSON.stringify({ tags: [{ name: opts['add-tag'] }] })
          );
          tagObj = created.tags[0];
          console.log(`🏷️  Tag "${opts['add-tag']}" created`);
        } else {
          tagObj = tagResult.tags[0];
        }

        console.log(`📦 Updating ${posts.length} posts with tag "${opts['add-tag']}"...`);
        let updated = 0;
        for (const post of posts) {
          try {
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
            console.error(`\n   ⚠️ Error on "${post.title}": ${JSON.stringify(err)}`);
          }
        }
        console.log(`\n✅ ${updated} posts updated`);
        break;
      }

      case 'posts:export': {
        const output = opts.output || `/tmp/ghost-export-${Date.now()}.json`;
        const posts = await browseAll('posts', '', '');
        fs.writeFileSync(output, JSON.stringify({ posts, exported_at: new Date().toISOString() }, null, 2));
        console.log(`✅ ${posts.length} posts exported to ${output}`);
        break;
      }

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

      case 'images:upload': {
        if (!opts.file) throw new Error('--file is required');
        const result = await uploadFile('/images/upload/', opts.file);
        console.log(JSON.stringify(result, null, 2));
        break;
      }

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
            if (!opts.id && !opts.slug) throw new Error('--id or --slug is required');
            const id = opts.slug ? `slug/${opts.slug}` : opts.id;
            result = await apiRequest('GET', `/${plural}/${id}/`);
            break;
          case 'create':
            if (!opts.json) throw new Error('--json is required');
            result = await apiRequest('POST', `/${plural}/`,
              JSON.stringify({ [plural]: [JSON.parse(opts.json)] }));
            break;
          case 'update':
            if (!opts.id) throw new Error('--id is required');
            const updateData = JSON.parse(opts.json);
            if (!updateData.updated_at) {
              const current = await apiRequest('GET', `/${plural}/${opts.id}/`);
              updateData.updated_at = current[plural]?.[0]?.updated_at;
            }
            result = await apiRequest('PUT', `/${plural}/${opts.id}/`,
              JSON.stringify({ [plural]: [updateData] }));
            break;
          case 'delete':
            if (!opts.id) throw new Error('--id is required');
            await apiRequest('DELETE', `/${plural}/${opts.id}/`);
            console.log('✅ Deleted');
            return;
          default:
            throw new Error(`Unknown action: "${action}"`);
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
