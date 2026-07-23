"""Public read API views.

No auth in the MVP (single user, local). DRF's default permission with no
DEFAULT_PERMISSION_CLASSES set is AllowAny, so these are open reads.

Split by domain (2026-07-22), mirroring models/ and serializers/, plus
options.py and cash.py for the cross-domain aggregates. This barrel keeps
`from repairs import views` / `from repairs.views import X` working (urls.py).
"""

from .cash import CashSummaryView
from .exits import ExitCreateView, ExitUpdateView
from .inventory import DeviceBulkCreateView, DeviceDetailView, InventoryListView
from .options import OptionsView
from .purchases import PurchaseArriveView, PurchaseDetailView, PurchaseListCreateView
from .reference import LaneListView, ReferenceListView
from .repairlog import (
    MeasurementCreateView,
    MeasurementUpdateView,
    NoteCreateView,
    NoteUpdateView,
    RepairCreateView,
    RepairUpdateView,
)

__all__ = [
    "CashSummaryView",
    "DeviceBulkCreateView",
    "DeviceDetailView",
    "ExitCreateView",
    "ExitUpdateView",
    "InventoryListView",
    "LaneListView",
    "MeasurementCreateView",
    "MeasurementUpdateView",
    "NoteCreateView",
    "NoteUpdateView",
    "OptionsView",
    "PurchaseArriveView",
    "PurchaseDetailView",
    "PurchaseListCreateView",
    "ReferenceListView",
    "RepairCreateView",
    "RepairUpdateView",
]
