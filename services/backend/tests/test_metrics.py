from transitpulse.metrics import Metrics


def test_prometheus_metrics_keep_labels_and_bounded_samples() -> None:
    metrics = Metrics()
    metrics.increment("transitpulse_http_requests_total", {"status": "200"})
    metrics.observe("transitpulse_http_request_duration_seconds", 0.25, {"path": "/api/v1/live"})

    rendered = metrics.render()

    assert 'transitpulse_http_requests_total{status="200"} 1' in rendered
    assert 'transitpulse_http_request_duration_seconds_count{path="/api/v1/live"} 1' in rendered


def test_prometheus_metrics_escape_label_values() -> None:
    metrics = Metrics()
    metrics.increment("transitpulse_example_total", {"label": 'a"b\nc'})

    assert 'label="a\\"b\\nc"' in metrics.render()


def test_duration_totals_do_not_reset_when_the_sample_window_rolls() -> None:
    metrics = Metrics()
    for _ in range(1005):
        metrics.observe("duration", 1.0)
    metrics.gauge("connections", 3)
    metrics.gauge("connections", 1)
    assert "duration_count 1005" in metrics.render()
    assert "duration_sum 1005.000000" in metrics.render()
    assert "connections 1" in metrics.render()
