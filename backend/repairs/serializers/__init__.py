"""API serializers.

Inventory list/create + device detail (with nested repairs and steps) on the read
side; device and step write paths for the create/edit modals. Heavier write paths
(measurements, parts, media) stay in the Django admin for now.

Split by domain (2026-07-22), mirroring models/: purchases, reference, inventory,
repairlog. This barrel keeps `from repairs.serializers import X` working.
"""

from .exits import ExitSerializer, ExitWriteSerializer
from .inventory import (
    DeviceBulkCreateSerializer,
    DeviceDetailSerializer,
    DeviceWriteSerializer,
    InventoryDeviceSerializer,
)
from .purchases import (
    PurchaseDetailSerializer,
    PurchaseSerializer,
    PurchaseUnitSerializer,
    PurchaseWriteSerializer,
)
from .reference import (
    STALE_AFTER_DAYS,
    CompPullSerializer,
    DeviceReferenceSerializer,
    IssueSerializer,
    LaneSerializer,
    RevisionSerializer,
    VariantSerializer,
)
from .stock import (
    RecountSerializer,
    StockIntakeSerializer,
    StockIntakeWriteSerializer,
    StockItemSerializer,
    StockItemWriteSerializer,
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
    "ExitSerializer",
    "ExitWriteSerializer",
    "InventoryDeviceSerializer",
    "IssueSerializer",
    "LaneSerializer",
    "MeasurementSerializer",
    "MeasurementWriteSerializer",
    "NoteSerializer",
    "NoteWriteSerializer",
    "PurchaseDetailSerializer",
    "PurchaseSerializer",
    "PurchaseUnitSerializer",
    "PurchaseWriteSerializer",
    "RecountSerializer",
    "RepairCreateSerializer",
    "RepairWithNotesSerializer",
    "RepairWriteSerializer",
    "RevisionSerializer",
    "StockIntakeSerializer",
    "StockIntakeWriteSerializer",
    "StockItemSerializer",
    "StockItemWriteSerializer",
    "VariantSerializer",
]
