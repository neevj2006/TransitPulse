from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_production_compose_keeps_state_services_private() -> None:
    compose = (PROJECT_ROOT / "infra" / "compose.production.yaml").read_text(encoding="utf-8")

    assert "internal: true" in compose
    assert '"${HTTP_PORT:-80}:80"' in compose
    assert '"${HTTPS_PORT:-443}:443"' in compose
    assert "condition: service_completed_successfully" in compose
    assert "stop_grace_period" in compose


def test_production_images_use_pinned_runtimes_and_non_root_users() -> None:
    backend = (PROJECT_ROOT / "services" / "backend" / "Dockerfile").read_text(encoding="utf-8")
    frontend = (PROJECT_ROOT / "apps" / "web" / "Dockerfile").read_text(encoding="utf-8")

    assert "python:3.12.8-slim-bookworm" in backend
    assert "USER transitpulse" in backend
    assert "node:22.14.0-alpine3.20" in frontend
    assert "USER nextjs" in frontend


def test_production_configuration_has_a_cors_origin_list() -> None:
    environment = (PROJECT_ROOT / "infra" / ".env.example").read_text(encoding="utf-8")

    assert 'TP_ALLOWED_ORIGINS=["https://transitpulse.example.com"]' in environment
