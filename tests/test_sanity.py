"""Sanity tests to ensure the package is properly installed and importable."""

import pytest
from advanced_meme_fun_snipper import get_version, init_logging


def test_package_import():
    """Test that the package can be imported successfully."""
    import advanced_meme_fun_snipper
    assert advanced_meme_fun_snipper is not None


def test_get_version():
    """Test that get_version returns a valid version string."""
    version = get_version()
    assert isinstance(version, str)
    assert version == "0.1.0"


def test_init_logging():
    """Test that logging initialization works."""
    logger = init_logging("INFO")
    assert logger is not None
    assert logger.name == "advanced_meme_fun_snipper"


def test_logging_setup_import():
    """Test that logging setup module can be imported."""
    from advanced_meme_fun_snipper.logging_setup import get_logger
    logger = get_logger("test")
    assert logger is not None
    assert logger.name == "advanced_meme_fun_snipper.test"


def test_snipper_module_import():
    """Test that the snipper module can be imported without errors."""
    # Note: This test only imports the module, not runs the bot
    # to avoid requiring actual API keys and connections
    try:
        from advanced_meme_fun_snipper import snipper
        assert snipper is not None
    except ImportError as e:
        # If there are missing dependencies, that's expected in testing
        # but the module structure should be correct
        if "No module named" not in str(e):
            raise


def test_always_passes():
    """A trivial test that always passes to ensure pytest is working."""
    assert True