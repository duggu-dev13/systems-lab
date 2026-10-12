import httpx

from lb.retry import may_retry


def test_connect_error_is_retried_even_for_post():
    assert may_retry("POST", httpx.ConnectError("refused")) is True

def test_connect_timeout_is_retried_even_for_post():
    assert may_retry("POST", httpx.ConnectTimeout("slow connect")) is True

def test_read_timeout_is_not_retried_for_post():
    assert may_retry("POST", httpx.ReadTimeout("no reply")) is False

def test_connection_reset_is_not_retried_for_patch():
    assert may_retry("PATCH", httpx.ReadError("reset")) is False

def test_read_timeout_is_retried_for_get():
    assert may_retry("GET", httpx.ReadTimeout("no reply")) is True

def test_method_name_is_case_insensitive():
    assert may_retry("get", httpx.ReadError("reset")) is True

def test_unsafe_flag_allows_post_retry():
    assert may_retry("POST", httpx.ReadTimeout("no reply"), retry_unsafe=True) is True

def test_classify_labels_each_failure_kind():
    from lb.retry import classify
    assert classify(httpx.ConnectError("x")) == "connect_failed"
    assert classify(httpx.ConnectTimeout("x")) == "connect_failed"
    assert classify(httpx.ReadTimeout("x")) == "timeout"
    assert classify(httpx.ReadError("x")) == "error"