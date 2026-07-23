from importlib import import_module


def test_gtfs_realtime_dependency_imports() -> None:
    module = import_module("google.transit.gtfs_realtime_pb2")
    assert getattr(module, "FeedMessage", None) is not None
