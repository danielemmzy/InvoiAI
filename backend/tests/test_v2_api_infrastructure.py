from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v2_api_surface_is_registered():
    source = (ROOT / "app" / "main.py").read_text()
    assert 'prefix="/api/v2"' in source
    assert 'prefix="/api/v2"' in source
    assert 'prefix="/api/v1"' not in source


def test_redis_is_used_for_rate_limiting_and_cache():
    limiter = (ROOT / "app" / "core" / "limiter.py").read_text()
    redis = (ROOT / "app" / "core" / "redis.py").read_text()
    assert "storage_uri=settings.redis_url" in limiter
    assert "settings.redis_max_connections" in redis


def test_v2_oauth_redirects_are_versioned():
    config = (ROOT / "app" / "core" / "config.py").read_text()
    assert "/api/v2/integrations/quickbooks/callback" in config
    assert "/api/v2/integrations/xero/callback" in config


def test_v2_read_heavy_routes_use_cache():
    for relative in (
        "app/routers/industries_v2.py",
        "app/routers/vendors.py",
        "app/routers/insights.py",
        "app/routers/organizations.py",
    ):
        source = (ROOT / relative).read_text()
        assert "from app.core.cache import cache" in source
