import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]


def load_app():
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from main import app

    return app


def test_app_imports():
    app = load_app()

    assert app.title == "LIMS API"


def test_core_routes_are_registered():
    app = load_app()
    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/api/machines" in paths
    assert "/api/recipes" in paths
    assert "/api/dispatches" in paths
