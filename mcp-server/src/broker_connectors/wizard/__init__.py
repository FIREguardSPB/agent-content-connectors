"""Local web wizard so a non-technical person can connect an account with no
terminal, no config files, and no Nango dashboard."""
from .server import main, run

__all__ = ["run", "main"]
