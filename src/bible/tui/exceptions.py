class BibleTUIError(Exception):
    """Base exception class for Bible TUI errors."""


class BibleTUIFetchError(BibleTUIError):
    """Exception raised for errors during fetching chapters or verses."""
