// k6-smoke.js — 30-second smoke test with the two thresholds that gate a PR.
//
// RUN
//   k6 run --env BASE_URL=https://staging.example.test perf/k6-smoke.js
// CI
//   see github-actions-perf.yml (grafana/setup-k6-action + grafana/run-k6-action)
//
// A failed threshold makes k6 exit non-zero. That non-zero exit is the gate.
// The numbers below are duplicated by hand from perf-budgets.md — keep them equal.
// Never point this at production. See ../README.md.
//
// Verified against https://grafana.com/docs/k6/latest/using-k6/thresholds/ on 2026-09-07.

import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<300'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const list = http.get(`${BASE_URL}/api/v1/items?page=0&size=20`);
  check(list, { 'list status is 200': (r) => r.status === 200 });

  const detail = http.get(`${BASE_URL}/api/v1/items/1`);
  check(detail, { 'detail status is 200': (r) => r.status === 200 });
}
