from django.urls import path

from .views import (
    DeviceBulkCreateView,
    DeviceDetailView,
    InventoryListView,
    LaneListView,
    MeasurementCreateView,
    MeasurementUpdateView,
    OptionsView,
    ReferenceListView,
    NoteCreateView,
    NoteUpdateView,
    PurchaseListCreateView,
    PurchaseUpdateView,
    RepairCreateView,
    RepairUpdateView,
)

urlpatterns = [
    path("inventory/", InventoryListView.as_view(), name="inventory"),
    path("inventory/bulk/", DeviceBulkCreateView.as_view(), name="inventory-bulk"),
    path("inventory/<int:pk>/", DeviceDetailView.as_view(), name="device-detail"),
    path("reference/", ReferenceListView.as_view(), name="reference"),
    path("lanes/", LaneListView.as_view(), name="lanes"),
    path("repairs/", RepairCreateView.as_view(), name="repair-create"),
    path("repairs/<int:pk>/", RepairUpdateView.as_view(), name="repair-update"),
    path("notes/", NoteCreateView.as_view(), name="note-create"),
    path("notes/<int:pk>/", NoteUpdateView.as_view(), name="note-update"),
    path("measurements/", MeasurementCreateView.as_view(), name="measurement-create"),
    path("measurements/<int:pk>/", MeasurementUpdateView.as_view(), name="measurement-update"),
    path("purchases/", PurchaseListCreateView.as_view(), name="purchases"),
    path("purchases/<int:pk>/", PurchaseUpdateView.as_view(), name="purchase-update"),
    path("options/", OptionsView.as_view(), name="options"),
]

