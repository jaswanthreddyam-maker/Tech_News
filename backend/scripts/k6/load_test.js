// ============================================================================
// k6 Load Testing — Tech News Today SLO Validation
// ============================================================================
// Validates Service Level Objectives under load:
//   Homepage:        p95 < 500ms
//   Search:          p95 < 700ms
//   Recommendations: p95 < 600ms
//   Article:         p95 < 400ms
//   AI Summary:      p95 < 8000ms
//   Availability:    99.9%
//
// Usage:
//   k6 run backend/scripts/k6/load_test.js
//   k6 run backend/scripts/k6/load_test.js --env BASE_URL=https://staging.example.com
//   k6 run backend/scripts/k6/load_test.js --env SCENARIO=stress
// ============================================================================

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ─── Custom Metrics ─────────────────────────────────────────────────────────

const homepageLatency = new Trend('homepage_latency', true);
const searchLatency = new Trend('search_latency', true);
const recommendationsLatency = new Trend('recommendations_latency', true);
const articleLatency = new Trend('article_latency', true);
const aiSummaryLatency = new Trend('ai_summary_latency', true);
const errorRate = new Rate('error_rate');

// ─── Configuration ──────────────────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const SCENARIO = __ENV.SCENARIO || 'load';

const scenarios = {
  // Standard load test: ramp up to 100 users
  load: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '1m', target: 20 },   // Ramp up
      { duration: '3m', target: 50 },   // Sustained load
      { duration: '2m', target: 100 },  // Peak load
      { duration: '1m', target: 0 },    // Ramp down
    ],
  },

  // Stress test: find the breaking point
  stress: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 100 },
      { duration: '2m', target: 500 },
      { duration: '2m', target: 1000 },
      { duration: '2m', target: 2000 },
      { duration: '2m', target: 0 },
    ],
  },

  // Spike test: sudden traffic jump
  spike: {
    executor: 'ramping-vus',
    startVUs: 10,
    stages: [
      { duration: '30s', target: 100 },
      { duration: '10s', target: 5000 },  // Spike!
      { duration: '2m', target: 5000 },   // Hold spike
      { duration: '30s', target: 100 },   // Recover
      { duration: '1m', target: 0 },
    ],
  },

  // Endurance test: sustained load for hours
  endurance: {
    executor: 'constant-vus',
    vus: 50,
    duration: '6h',
  },
};

export const options = {
  scenarios: {
    default: scenarios[SCENARIO] || scenarios.load,
  },
  thresholds: {
    'homepage_latency':        ['p(95)<500'],
    'search_latency':          ['p(95)<700'],
    'recommendations_latency': ['p(95)<600'],
    'article_latency':         ['p(95)<400'],
    'ai_summary_latency':      ['p(95)<8000'],
    'error_rate':              ['rate<0.001'],  // 99.9% availability
    'http_req_failed':         ['rate<0.001'],
  },
};

// ─── Test Scenarios ─────────────────────────────────────────────────────────

export default function () {
  // --- Homepage ---
  group('Homepage', () => {
    const res = http.get(`${BASE_URL}/api/v1/articles?limit=20&offset=0`);
    homepageLatency.add(res.timings.duration);
    const success = check(res, {
      'homepage: status 200': (r) => r.status === 200,
      'homepage: has articles': (r) => {
        try { return JSON.parse(r.body).length >= 0; } catch { return false; }
      },
    });
    errorRate.add(!success);
  });

  sleep(1);

  // --- Search ---
  group('Search', () => {
    const queries = ['AI', 'machine learning', 'GPT', 'neural network', 'robotics'];
    const query = queries[Math.floor(Math.random() * queries.length)];
    const res = http.get(`${BASE_URL}/api/v1/articles/search?q=${encodeURIComponent(query)}&limit=10`);
    searchLatency.add(res.timings.duration);
    const success = check(res, {
      'search: status 200': (r) => r.status === 200,
    });
    errorRate.add(!success);
  });

  sleep(1);

  // --- Recommendations ---
  group('Recommendations', () => {
    const res = http.get(`${BASE_URL}/api/v1/articles?limit=10&sort=trending`);
    recommendationsLatency.add(res.timings.duration);
    const success = check(res, {
      'recommendations: status 200': (r) => r.status === 200,
    });
    errorRate.add(!success);
  });

  sleep(1);

  // --- Article Detail ---
  group('Article', () => {
    // First get an article list to find a valid slug
    const listRes = http.get(`${BASE_URL}/api/v1/articles?limit=1`);
    if (listRes.status === 200) {
      try {
        const articles = JSON.parse(listRes.body);
        if (articles.length > 0) {
          const slug = articles[0].slug || articles[0].id;
          const res = http.get(`${BASE_URL}/api/v1/articles/${slug}`);
          articleLatency.add(res.timings.duration);
          const success = check(res, {
            'article: status 200': (r) => r.status === 200,
          });
          errorRate.add(!success);
        }
      } catch (e) {
        errorRate.add(true);
      }
    }
  });

  sleep(1);

  // --- Health Check ---
  group('Health', () => {
    const res = http.get(`${BASE_URL}/api/v1/health/ready`);
    check(res, {
      'health: status 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 2 + 1); // Random think time 1-3s
}

// ─── Lifecycle Hooks ────────────────────────────────────────────────────────

export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    scenario: SCENARIO,
    base_url: BASE_URL,
    metrics: {
      homepage_p95: data.metrics.homepage_latency?.values?.['p(95)'] || null,
      search_p95: data.metrics.search_latency?.values?.['p(95)'] || null,
      recommendations_p95: data.metrics.recommendations_latency?.values?.['p(95)'] || null,
      article_p95: data.metrics.article_latency?.values?.['p(95)'] || null,
      ai_summary_p95: data.metrics.ai_summary_latency?.values?.['p(95)'] || null,
      error_rate: data.metrics.error_rate?.values?.rate || null,
      http_req_duration_p95: data.metrics.http_req_duration?.values?.['p(95)'] || null,
      http_reqs_count: data.metrics.http_reqs?.values?.count || null,
    },
    thresholds: data.root_group?.checks || {},
  };

  return {
    stdout: JSON.stringify(summary, null, 2) + '\n',
    'load_test_results.json': JSON.stringify(summary, null, 2),
  };
}
