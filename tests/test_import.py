"""Test basic imports."""


def test_import_main():
    """Test that main module can be imported."""
    import main  # noqa: F401


def test_import_orchestrator():
    """Test that orchestrator can be imported."""
    from src import orchestrator  # noqa: F401


def test_import_events():
    """Test that events module can be imported."""
    from src import events  # noqa: F401


def test_import_actions():
    """Test that actions module can be imported."""
    from src import actions  # noqa: F401


def test_import_template_match():
    """Test that template_match can be imported."""
    from src import template_match  # noqa: F401


def test_import_scraper():
    """Test that scraper can be imported."""
    from src import scraper  # noqa: F401
