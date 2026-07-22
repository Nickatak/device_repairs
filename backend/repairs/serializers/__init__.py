"""API serializers.

Inventory list/create + device detail (with nested repairs and steps) on the read
side; device and step write paths for the create/edit modals. Heavier write paths
(measurements, parts, media) stay in the Django admin for now.

Split by domain (2026-07-22), mirroring models/: purchases, reference, inventory,
repairlog. This barrel keeps `from repairs.serializers import X` working.
"""

from .inventory import (
    DeviceBulkCreateSerializer,
    DeviceDetailSerializer,
    DeviceWriteSerializer,
    InventoryDeviceSerializer,
)
from .purchases import PurchaseSerializer, PurchaseWriteSerializer
from .reference import (
    STALE_AFTER_DAYS,
    CompPullSerializer,
    DeviceReferenceSerializer,
    LaneSerializer,
)
from .repairlog import (
    COMPLETED_REPAIR_ERROR,
    PHASE_FIELDS,
    MeasurementSerializer,
    MeasurementWriteSerializer,
    NoteSerializer,
    NoteWriteSerializer,
    RepairCreateSerializer,
    RepairWithNotesSerializer,
    RepairWriteSerializer,
)

__all__ = [
    "COMPLETED_REPAIR_ERROR",
    "PHASE_FIELDS",
    "STALE_AFTER_DAYS",
    "CompPullSerializer",
    "DeviceBulkCreateSerializer",
    "DeviceDetailSerializer",
    "DeviceReferenceSerializer",
    "DeviceWriteSerializer",
    "InventoryDeviceSerializer",
    "LaneSerializer",
    "MeasurementSerializer",
    "MeasurementWriteSerializer",
    "NoteSerializer",
    "NoteWriteSerializer",
    "PurchaseSerializer",
    "PurchaseWriteSerializer",
    "RepairCreateSerializer",
    "RepairWithNotesSerializer",
    "RepairWriteSerializer",
]
