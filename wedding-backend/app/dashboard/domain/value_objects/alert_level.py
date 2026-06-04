"""Alert level enumeration."""
from __future__ import annotations
from enum import Enum


class AlertLevel(str, Enum):
    """Alert severity level."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
