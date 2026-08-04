"""API serializers.

Inventory list/create + device detail (with nested repairs and steps) on the read
side; device and step write paths for the create/edit modals. Media uploads land
via the API since 2026-07-24 (GPS-stripped, EXIF taken_at); Parts stay admin-side.

Split by domain (2026-07-22), mirroring models/: orders, reference, inventory,
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
from .orders import (
    OrderDetailSerializer,
    OrderSerializer,
    OrderUnitSerializer,
    OrderWriteSerializer,
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
    NoteTemplateSerializer,
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
    "NoteTemplateSerializer",
    "NoteWriteSerializer",
    "OrderDetailSerializer",
    "OrderSerializer",
    "OrderUnitSerializer",
    "OrderWriteSerializer",
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
