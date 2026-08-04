"""Repair working-log domain model.

The shape and decisions behind these models live in ../../docs/domain.md (Settled tier).
The bench spine is Note: symptoms, faults, damage are observations *within* notes,
not nouns. Ledger spine: Order (money) → Device (unit) → Repair (bench work).

Split by domain (2026-07-22): orders (money in), reference (price-sheet
catalog), inventory (physical units), repairlog (bench work). This barrel keeps
`from repairs.models import X` working everywhere, including migrations.
"""

from .exits import Exit
from .inventory import Device, DeviceNote, Location
from .orders import Order, Source
from .reference import CompPull, DeviceReference, Issue, Lane, Revision, Variant
from .repairlog import (
    Measurement,
    Media,
    Note,
    NoteTemplate,
    NoteTemplateEntry,
    NoteTemplateMeasurement,
    Part,
    Repair,
)
from .stock import StockIntake, StockItem

__all__ = [
    "CompPull",
    "Device",
    "DeviceNote",
    "DeviceReference",
    "Exit",
    "Issue",
    "Lane",
    "Location",
    "Measurement",
    "Media",
    "Note",
    "NoteTemplate",
    "NoteTemplateEntry",
    "NoteTemplateMeasurement",
    "Part",
    "Order",
    "Repair",
    "Revision",
    "Source",
    "StockIntake",
    "StockItem",
    "Variant",
]
