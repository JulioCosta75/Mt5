"""Static Educador explanation record (Stage 1 — no AI)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Explanation:
    """One glossary entry: stable id, short definition, one concrete example."""

    id: str
    title: str
    definition: str
    example: str
