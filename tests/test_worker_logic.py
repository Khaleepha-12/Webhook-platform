import hashlib
import hmac

from app.worker import BASE_DELAY, MAX_DELAY, backoff_seconds, sign


def test_backoff_stays_between_zero_and_ceiling():
    for retry in range(10):
        ceiling = min(MAX_DELAY, BASE_DELAY * 2**retry)
        for _ in range(200):
            assert 0 <= backoff_seconds(retry) <= ceiling


def test_backoff_is_capped_for_large_retry_counts():
    for _ in range(200):
        assert backoff_seconds(50) <= MAX_DELAY


def test_sign_is_deterministic():
    assert sign("secret", "1000", '{"a":1}') == sign("secret", "1000", '{"a":1}')


def test_sign_changes_when_body_changes():
    assert sign("secret", "1000", '{"a":1}') != sign("secret", "1000", '{"a":2}')


def test_sign_changes_when_timestamp_changes():
    assert sign("secret", "1000", "{}") != sign("secret", "1001", "{}")


def test_sign_changes_when_secret_changes():
    assert sign("secret-a", "1000", "{}") != sign("secret-b", "1000", "{}")


def test_sign_matches_independent_hmac():
    expected = hmac.new(b"secret", b"1000.{}", hashlib.sha256).hexdigest()
    assert sign("secret", "1000", "{}") == expected