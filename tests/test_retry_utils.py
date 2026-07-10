"""Tests for retry_utils.retry_http."""

from unittest.mock import MagicMock, patch

import pytest

from retry_utils import retry_http


def test_retry_http_success_first_attempt():
    assert retry_http(lambda: 42) == 42


def test_retry_http_success_after_transient_failure():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ConnectionError("timeout")
        return "ok"

    with patch("retry_utils.time.sleep"):
        assert retry_http(flaky, attempts=3, exceptions=(ConnectionError,)) == "ok"
    assert calls["n"] == 2


def test_retry_http_exhausted_returns_none():
    with patch("retry_utils.time.sleep"):
        result = retry_http(lambda: (_ for _ in ()).throw(RuntimeError("fail")), attempts=2)
    assert result is None


def test_retry_http_respects_exception_filter():
    with patch("retry_utils.time.sleep"):
        with pytest.raises(ValueError):
            retry_http(lambda: (_ for _ in ()).throw(ValueError("nope")), exceptions=(ConnectionError,))


def test_retry_http_exponential_backoff_delays():
    fn = MagicMock(side_effect=[OSError("a"), OSError("b"), "done"])
    with patch("retry_utils.time.sleep") as sleep:
        assert retry_http(fn, attempts=3, base_delay_s=0.5, exceptions=(OSError,)) == "done"
    sleep.assert_any_call(0.5)
    sleep.assert_any_call(1.0)
    assert fn.call_count == 3
