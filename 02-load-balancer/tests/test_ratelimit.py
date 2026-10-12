from backend.ratelimit import build_limiter, client_key


def test_off_by_default():
    assert build_limiter({}) is None

def test_limit_zero_means_off():
    assert build_limiter({"LIMIT": "0"}) is None

def test_builds_fixed_window_from_env():
    limiter = build_limiter({"ALGO": "fixed_window", "LIMIT": "2", "WINDOW": "1"})
    results = [limiter.check("alice").allowed for _ in range(3)]
    assert results == [True, True, False]

def test_builds_token_bucket_from_env():
    limiter = build_limiter({"ALGO": "token_bucket", "LIMIT": "2", "WINDOW": "1"})
    results = [limiter.check("alice").allowed for _ in range(3)]
    assert results == [True, True, False]

def test_unknown_algorithm_is_rejected():
    try:
        build_limiter({"ALGO": "nonsense", "LIMIT": "5"})
    except ValueError:
        return
    assert False, "expected ValueError"

def test_client_key_uses_forwarded_header():
    assert client_key({"x-forwarded-for": "10.0.0.7"}, "127.0.0.1") == "10.0.0.7"

def test_client_key_takes_first_address_in_chain():
    assert client_key({"x-forwarded-for": "10.0.0.7, 192.168.1.1"}, "127.0.0.1") == "10.0.0.7"

def test_client_key_falls_back_to_connection_address():
    assert client_key({}, "127.0.0.1") == "127.0.0.1"