"""Small dependency-free Prometheus exposition for operational metrics."""

from collections import defaultdict
from threading import Lock


class Metrics:
    """In-process metrics with deliberately bounded label cardinality."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = defaultdict(
            list
        )
        self._lock = Lock()
        self._totals: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[int, float]] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

    @staticmethod
    def _labels(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
        return tuple(sorted((labels or {}).items()))

    @staticmethod
    def _render_labels(labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return ""

        def quote(value: str) -> str:
            return (
                value.replace(chr(92), chr(92) * 2)
                .replace(chr(34), chr(92) + chr(34))
                .replace(chr(10), chr(92) + "n")
            )

        escaped = (f'{key}="{quote(value)}"' for key, value in labels)
        return "{" + ",".join(escaped) + "}"

    def increment(self, name: str, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            self._counters[name, self._labels(labels)] += 1

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            key = (name, self._labels(labels))
            count, total = self._totals.get(key, (0, 0.0))
            self._totals[key] = (count + 1, total + value)
            samples = self._histograms[key]
            samples.append(value)
            del samples[:-1_000]

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            self._gauges[name, self._labels(labels)] = value

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._gauges.items()):
                lines.append(f"{name}{self._render_labels(labels)} {value:g}")
            for (name, labels), value in sorted(self._counters.items()):
                lines.append(f"{name}{self._render_labels(labels)} {value:g}")
            for (name, labels), samples in sorted(self._histograms.items()):
                if samples:
                    suffix = self._render_labels(labels)
                    count, total = self._totals[name, labels]
                    lines.extend(
                        (
                            f"{name}_count{suffix} {count}",
                            f"{name}_sum{suffix} {total:.6f}",
                            f"{name}_max{suffix} {max(samples):.6f}",
                        )
                    )
        return "\n".join(lines) + ("\n" if lines else "")
