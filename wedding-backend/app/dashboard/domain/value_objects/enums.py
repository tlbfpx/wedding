"""Additional enumerations for dashboard module."""
from __future__ import annotations
from enum import Enum


class DecisionDimension(str, Enum):
    """Decision support analysis dimension."""
    SOURCE = "source"
    SERVICE = "service"
    SUPPLIER = "supplier"
