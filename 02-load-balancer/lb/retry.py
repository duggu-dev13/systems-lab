import httpx

# Methods that HTTP defines as safe to repeat: doing them twice has the same
# effect as doing them once. POST and PATCH are NOT in this set.
IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}

# Failures where the request never reached the backend.
NEVER_REACHED = (httpx.ConnectError, httpx.ConnectTimeout)


def may_retry(method, exc, retry_unsafe=False):
    """Decide whether a failed attempt may be retried on another backend."""
    if isinstance(exc, NEVER_REACHED):
        return True                    # nothing happened on the backend: safe for any method
    # Anything else (read timeout, connection reset mid-response...) is ambiguous:
    # the backend may have done the work and only the reply was lost.
    return method.upper() in IDEMPOTENT_METHODS or retry_unsafe