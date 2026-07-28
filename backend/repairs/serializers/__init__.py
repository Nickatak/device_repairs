"""API serializers.

Inventory list/create + device detail (with nested repairs and steps) on the read
side; device and step write paths for the create/edit modals. Media uploads land
via the API since 2026-07-24 (GPS-stripped, EXIF taken_at); Parts stay admin-side.

Split by domain (2026-07-22), mirroring models/: purchases, reference, inventory,
repairlog. This barrel keeps `from repairs.serializers import X` working.
"""

from .exits import ExitSerializer, ExitWriteSerializer
from .inventory import (
    DeviceBulkCreateSerializer,
    DeviceDetailSerializer,
    DeviceNoteSerializer,
    DeviceNoteWriteSerializer,
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
    RevisionWriteSerializer,
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
    MediaSerializer,
    MediaWriteSerializer,
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
    "DeviceNoteSerializer",
    "DeviceNoteWriteSerializer",
    "DeviceReferenceSerializer",
    "DeviceWriteSerializer",
    "ExitSerializer",
    "ExitWriteSerializer",
    "InventoryDeviceSerializer",
    "IssueSerializer",
    "LaneSerializer",
    "MeasurementSerializer",
    "MeasurementWriteSerializer",
    "MediaSerializer",
    "MediaWriteSerializer",
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
    "RevisionWriteSerializer",
    "StockIntakeSerializer",
    "StockIntakeWriteSerializer",
    "StockItemSerializer",
    "StockItemWriteSerializer",
    "VariantSerializer",
]
