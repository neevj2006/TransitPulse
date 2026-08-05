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
