// Parity check for a read operation: call the old path and the new path with the same input,
// compare the two JSON bodies field by field, and fail the run on any difference.
//
// Synthetic and generic. Point it at a NON-production environment only.
//
//   k6 run -e BASE=https://staging.example.test \
//          -e OLD=/test/old/items -e NEW=/api/v2/items \
//          -e IDS=A-100,A-101,A-102 \
//          parity-read.k6.js
//
// Optional: -e TOKEN=... (sent as a bearer token), -e IGNORE=meta.requestId,meta.servedAt
//
// OLD is a test-only route that runs the old client exactly as production does and returns its final
// output as JSON. NEW returns what callers will receive after the switch. Both take the id as the
// last path segment.

import http from 'k6/http';
import { check, fail } from 'k6';
import { Counter } from 'k6/metrics';

const BASE = __ENV.BASE || fail('set BASE, for example -e BASE=https://staging.example.test');
const OLD = __ENV.OLD || '/test/old/items';
const NEW = __ENV.NEW || '/api/v2/items';
const IDS = (__ENV.IDS || '').split(',').map((s) => s.trim()).filter(Boolean);
// Paths the consumer never sees. Keep this list short and explain each entry where you set it.
const IGNORE = new Set((__ENV.IGNORE || '').split(',').map((s) => s.trim()).filter(Boolean));

const differences = new Counter('parity_differences');

export const options = {
  vus: 1,
  iterations: Math.max(IDS.length, 1),
  thresholds: {
    parity_differences: ['count==0'],
    checks: ['rate==1'],
  },
};

const params = {
  headers: Object.assign(
    { Accept: 'application/json' },
    __ENV.TOKEN ? { Authorization: `Bearer ${__ENV.TOKEN}` } : {},
  ),
  tags: { name: 'parity' },
};

function typeOf(v) {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  return typeof v;
}

// Returns a list of differences. Each one names the path, what the old path returned and what the
// new path returned. Missing fields, null and empty values are different on purpose.
export function compare(oldValue, newValue, path = '$', out = []) {
  if (IGNORE.has(path.replace(/^\$\.?/, ''))) return out;
  const a = typeOf(oldValue);
  const b = typeOf(newValue);
  if (a !== b) {
    out.push({ path, kind: 'type', old: a, new: b });
    return out;
  }
  if (a === 'array') {
    if (oldValue.length !== newValue.length) {
      out.push({ path, kind: 'length', old: oldValue.length, new: newValue.length });
    }
    const n = Math.min(oldValue.length, newValue.length);
    for (let i = 0; i < n; i++) compare(oldValue[i], newValue[i], `${path}[${i}]`, out);
    return out;
  }
  if (a === 'object') {
    const keys = new Set([...Object.keys(oldValue), ...Object.keys(newValue)]);
    for (const k of keys) {
      const p = `${path}.${k}`;
      if (!(k in newValue)) out.push({ path: p, kind: 'missing-in-new', old: oldValue[k] });
      else if (!(k in oldValue)) out.push({ path: p, kind: 'extra-in-new', new: newValue[k] });
      else compare(oldValue[k], newValue[k], p, out);
    }
    return out;
  }
  if (a === 'number' && !Number.isSafeInteger(oldValue) && Number.isInteger(oldValue)) {
    out.push({ path, kind: 'unsafe-integer', old: oldValue, new: newValue });
  }
  if (oldValue !== newValue) out.push({ path, kind: 'value', old: oldValue, new: newValue });
  return out;
}

export default function () {
  const id = IDS[__ITER];
  if (!id) fail('set IDS, for example -e IDS=A-100,A-101');

  const oldRes = http.get(`${BASE}${OLD}/${encodeURIComponent(id)}`, params);
  const newRes = http.get(`${BASE}${NEW}/${encodeURIComponent(id)}`, params);

  const sameStatus = check(null, {
    [`${id}: same status (${oldRes.status} vs ${newRes.status})`]: () => oldRes.status === newRes.status,
  });
  if (!sameStatus) {
    differences.add(1);
    return;
  }
  // Same status from here on. When both failed the same way, the bodies are still compared:
  // the error shape is part of the contract too.

  let oldBody;
  let newBody;
  try {
    oldBody = oldRes.json();
    newBody = newRes.json();
  } catch (e) {
    differences.add(1);
    check(null, { [`${id}: both bodies are JSON`]: () => false });
    return;
  }

  const diff = compare(oldBody, newBody);
  differences.add(diff.length);
  check(null, { [`${id}: no differences`]: () => diff.length === 0 });
  for (const d of diff) console.warn(`[${id}] ${JSON.stringify(d)}`);
}
