import http from 'k6/http';
import { Counter, Trend } from 'k6/metrics';

const ok = new Counter('lb_ok');
const failed = new Counter('lb_failed');
const retried = new Counter('lb_retried');
const retriedLatency = new Trend('lb_retried_latency', true);

const RATE = parseInt(__ENV.RATE || '50');
const DURATION = __ENV.DURATION || '2m';
const KILL_AT = __ENV.KILL_AT || '10s';

export const options = {
  scenarios: {
    traffic: {
      executor: 'constant-arrival-rate',
      exec: 'traffic',
      rate: RATE,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
    chaos: {
      executor: 'per-vu-iterations',
      exec: 'killB',
      vus: 1,
      iterations: 1,
      startTime: KILL_AT,
    },
  },
};

export function traffic() {
  const res = http.get('http://127.0.0.1:8000/api/ping');
  if (res.status === 200) {
    ok.add(1);
    if (parseInt(res.headers['X-Attempts'] || '1') > 1) {
      retried.add(1);
      retriedLatency.add(res.timings.duration);
    }
  } else {
    failed.add(1);
  }
}

export function killB() {
  http.post('http://127.0.0.1:9002/_admin/die');
}