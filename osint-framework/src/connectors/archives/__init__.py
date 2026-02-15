"""
Web archive and historical data connectors.
"""

from .wayback_machine import WaybackMachineConnector, WaybackScreenshotsConnector

__all__ = [
    'WaybackMachineConnector',
    'WaybackScreenshotsConnector'
]
