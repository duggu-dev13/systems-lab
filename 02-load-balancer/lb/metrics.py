from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "lb_requests_total", "Responses sent to clients", ["status"])
ATTEMPTS = Counter(
    "lb_attempts_total", "Attempts made against backends", ["backend", "outcome"])
RETRIED = Counter(
    "lb_retried_requests_total", "Requests that needed more than one attempt")
DURATION = Histogram(
    "lb_request_duration_seconds", "Time to answer a client, including retries",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))
BACKEND_UP = Gauge(
    "lb_backend_up", "1 if the balancer considers the backend healthy", ["backend"])
IN_FLIGHT = Gauge(
    "lb_backend_in_flight", "Requests in flight (least_connections only)", ["backend"])
TRANSITIONS = Counter(
    "lb_health_transitions_total", "Backend status changes", ["backend", "to"])