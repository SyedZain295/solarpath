"""Tests for auth anomaly detection and lockout."""

from anomaly_detection import AnomalyConfig, AuthAnomalyTracker


def test_lockout_after_max_failures():
    tracker = AuthAnomalyTracker(AnomalyConfig(window_seconds=60, max_failures=3, block_seconds=120))
    for _ in range(3):
        locked = tracker.record_failure("test", identifier="user@x.com", ip="1.2.3.4")
    assert locked is True
    assert tracker.is_blocked("user@x.com", "1.2.3.4") is True


def test_failures_below_threshold_no_lockout():
    tracker = AuthAnomalyTracker(AnomalyConfig(window_seconds=60, max_failures=5, block_seconds=60))
    assert tracker.record_failure("test", identifier="a", ip="9.9.9.9") is False
    assert tracker.is_blocked("a", "9.9.9.9") is False


def test_reset_clears_state():
    tracker = AuthAnomalyTracker(AnomalyConfig(window_seconds=60, max_failures=1, block_seconds=60))
    tracker.record_failure("test", identifier="x", ip="1.1.1.1")
    assert tracker.is_blocked("x", "1.1.1.1")
    tracker.reset()
    assert not tracker.is_blocked("x", "1.1.1.1")
