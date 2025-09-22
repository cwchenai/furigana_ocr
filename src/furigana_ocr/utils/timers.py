"""Utility helpers for dealing with polling intervals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class FrequencyController:
    """Keeps track of when the next processing cycle should run."""

    interval: timedelta
    last_triggered: Optional[datetime] = None

    @classmethod
    def from_milliseconds(cls, value: int) -> "FrequencyController":
        return cls(interval=timedelta(milliseconds=value))

    def should_fire(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        if self.last_triggered is None:
            return True
        return now - self.last_triggered >= self.interval

    def mark_triggered(self, when: Optional[datetime] = None) -> None:
        self.last_triggered = when or datetime.utcnow()


__all__ = ["FrequencyController"]
