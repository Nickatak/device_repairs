"""Public read API views.

No auth in the MVP (single user, local). DRF's default permission with no
DEFAULT_PERMISSION_CLASSES set is AllowAny, so these are open reads.

Split by domain (2026-07-22), mirroring models/ and serializers/, plus
options.py and cash.py for the cross-domain aggregates. This barrel keeps
`from repairs import views` / `from repairs.views import X` working (urls.py).
"""

from .cash import CashSummaryView
from .exits import ExitCreateView, ExitUpdateView
from .inventory import (
    DeviceBulkCreateView,
    DeviceDetailView,
    DeviceNoteCreateView,
    DeviceNoteUpdateView,
    InventoryListView,
)
from .options import OptionsView
from .orders import OrderArriveView, OrderDetailView, OrderListCreateView
from .reference import (
    LaneListView,
    ReferenceListView,
    RevisionCreateView,
    RevisionUpdateView,
)
from .repairlog import (
    MeasurementCreateView,
    MeasurementUpdateView,
    MediaCreateView,
    MediaUpdateView,
    NoteCreateView,
    NoteTemplateDetailView,
    NoteTemplateListCreateView,
    NoteUpdateView,
    RepairCreateView,
    RepairUpdateView,
)
from .stock import (
    StockDetailView,
    StockIntakeCreateView,
    StockIntakeUpdateView,
    StockListCreateView,
    StockRecountView,
)

__all__ = [
    "CashSummaryView",
    "DeviceBulkCreateView",
    "DeviceDetailView",
    "DeviceNoteCreateView",
    "DeviceNoteUpdateView",
    "ExitCreateView",
    "ExitUpdateView",
    "InventoryListView",
    "LaneListView",
    "MeasurementCreateView",
    "MeasurementUpdateView",
    "MediaCreateView",
    "MediaUpdateView",
    "NoteCreateView",
    "NoteTemplateDetailView",
    "NoteTemplateListCreateView",
    "NoteUpdateView",
    "OptionsView",
    "OrderArriveView",
    "OrderDetailView",
    "OrderListCreateView",
    "ReferenceListView",
    "RevisionCreateView",
    "RevisionUpdateView",
    "RepairCreateView",
    "RepairUpdateView",
    "StockDetailView",
    "StockIntakeCreateView",
    "StockIntakeUpdateView",
    "StockListCreateView",
    "StockRecountView",
]
