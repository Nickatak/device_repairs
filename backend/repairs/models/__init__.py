"""Repair working-log domain model.

The shape and decisions behind these models live in ../../docs/domain.md (Settled tier).
The bench spine is Note: symptoms, faults, damage are observations *within* notes,
not nouns. Ledger spine: Purchase (money) → Device (unit) → Repair (bench work).

Split by domain (2026-07-22): purchases (money in), reference (price-sheet
catalog), inventory (physical units), repairlog (bench work). This barrel keeps
`from repairs.models import X` working everywhere, including migrations.
"""

from .exits import Exit
from .inventory import Device, Location
from .purchases import Purchase, Source
from .reference import CompPull, DeviceReference, Issue, Lane, Variant
from .repairlog import Measurement, Media, Note, Part, Repair

__all__ = [
    "CompPull",
    "Device",
    "DeviceReference",
    "Exit",
    "Issue",
    "Lane",
    "Location",
    "Measurement",
    "Media",
    "Note",
    "Part",
    "Purchase",
    "Repair",
    "Source",
    "Variant",
]
