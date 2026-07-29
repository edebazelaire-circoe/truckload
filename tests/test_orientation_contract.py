from __future__ import annotations

from pallet_optimizer.domain import CargoItem, DomainError, Shape


def test_rotation_only_swaps_floor_dimensions() -> None:
    item = CargoItem("PAL", "PAL", 0, Shape.PALLET, 1200, 800, 1500, 100, "A", 1)

    length_0, width_0, _, _ = item.oriented_dimensions(0)
    length_90, width_90, _, _ = item.oriented_dimensions(90)

    assert (length_0, width_0, item.height_mm) == (1200, 800, 1500)
    assert (length_90, width_90, item.height_mm) == (800, 1200, 1500)


def test_height_cannot_be_used_as_a_floor_orientation() -> None:
    item = CargoItem("PAL", "PAL", 0, Shape.PALLET, 1200, 800, 1500, 100, "A", 1)

    try:
        item.oriented_dimensions(180)
    except DomainError as exc:
        assert exc.diagnostic.code == "INVALID_ROTATION"
    else:
        raise AssertionError("An unsupported orientation was accepted")
