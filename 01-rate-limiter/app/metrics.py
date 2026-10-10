from prometheus_client import Counter, Histogram

REQUESTS = Counter(
    "rl_requests_total",
    "Requests by rate limiter decision",
    ["algorithm", "decision"],
)

DECISION_SECONDS = Histogram(
    "rl_decision_seconds",
    "Time the limiter itself takes to decide",
    ["algorithm"],
    buckets=(0.000005, 0.00001, 0.00005, 0.0001, 0.0005, 0.001, 0.005, 0.01),
)

HTTP_RESPONSES = Counter(
    "http_responses_total",
    "HTTP responses by status code",
    ["status"],
)

HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "Total time to handle a request",
)