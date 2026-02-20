"""
Dark Theme Stylesheet Loader

Loads and returns the dark theme QSS stylesheet.
"""

from pathlib import Path


def load_stylesheet() -> str:
    """
    Load the dark theme stylesheet.

    Returns:
        The QSS stylesheet as a string.
    """
    style_path = Path(__file__).parent / "dark_theme.qss"
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Failed to load stylesheet from {style_path}: {e}")
        return ""
