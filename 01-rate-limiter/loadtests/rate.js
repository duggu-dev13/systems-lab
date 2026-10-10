import http from 'k6/http';
import { Counter } from 'k6/metrics';

const allowed = new Counter('rl_allowed');
const rejected = new Counter('rl_rejected');

// Treat both 200 and 429 as expected, so k6 doesn't count 429 as a failure
http.setResponseCallback(http.expectedStatuses(200, 429));

const RATE = parseInt(__ENV.RATE || '300');
const DURATION = __ENV.DURATION || '30s';

export const options = {
  scenarios: {
    load: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/api/ping');
  if (res.status === 200) allowed.add(1);
  else if (res.status === 429) rejected.add(1);
}