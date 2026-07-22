"""Shared test fixtures."""

from repairs.models import DeviceReference, Lane


def make_ref(name="Test Model", brand="TestBrand", lane_name="console"):
    lane, _ = Lane.objects.get_or_create(name=lane_name)
    return DeviceReference.objects.create(lane=lane, brand=brand, name=name)
